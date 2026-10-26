using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.UI;
namespace Forge.Interface
{
    // Lot #657 : lieux des cellules tenues, couleur du maître, rouge si les départs dépassent les arrivées. Lecture seule.
    public sealed class LieuxDeCarte : MonoBehaviour
    {
        public const string RACINE = "Lieux de la carte", ENTETE = "Blanc : vos lieux. Couleurs : autres maîtres. Rouge : départs supérieurs aux arrivées sur trente jours.";
        public const float PERIODE_S = 2f, EPAISSEUR_KM = 0.05f; public static readonly Color ROUGE = new Color(0.86f, 0.05f, 0.04f); // « alerte » (#8B342E) rend un rose terne sur la carte éclairée
        const float TEINTE_MIN = 0.18f, ETENDUE_TEINTE = 0.5f, SATURATION = 0.7f, VALEUR = 0.75f, OPACITE_FOND = 0.72f; const uint PAS_DE_TEINTE = 500; // du jaune au bleu : ni blanc ni rouge
        public Func<long, LectureLieu> Lecteur; public Text Legende { get; private set; }
        public string TexteLegende => Legende != null ? Legende.text : null;
        public bool LectureEnVol => vol != null && !vol.IsCompleted;
        public event Action<string, IReadOnlyList<(long cell, LectureLieu lieu)>> Applique; // #658 : la maison et la réponse appliquée ; maison nulle quand l'ancien domaine est vidé
        CarteDessinee carte; CabinetDeCarte cabinet; Transform racine; Material bord; Image fond;
        readonly Dictionary<Color, Material> mats = new Dictionary<Color, Material>();
        readonly List<UnityEngine.Object> crees = new List<UnityEngine.Object>();
        Task<Paquet> vol; double prochaine; string peinte;
        sealed class Paquet { public string Maison; public List<(long cell, LectureLieu lieu)> Cellules; }
        public void Installer(Transform toile)
        {
            carte = GetComponent<CarteDessinee>(); cabinet = GetComponent<CabinetDeCarte>();
            // Un fond sombre translucide, à la taille du texte : lisible sur les terres claires, sans cacher les disques ni prendre les clics.
            fond = new GameObject("Fond de la légende", typeof(Image)).GetComponent<Image>(); var f = fond.rectTransform; f.SetParent(toile, false); f.anchorMin = f.anchorMax = f.pivot = new Vector2(0, 1); f.anchoredPosition = new Vector2(16, -104); fond.raycastTarget = false; fond.color = SocleInterface.Couleur("fond") * new Color(1f, 1f, 1f, OPACITE_FOND);
            Legende = SocleInterface.Texte(fond.transform, "Légende des lieux", 8, 4, 1100); Legende.alignment = TextAnchor.UpperLeft; Legende.horizontalOverflow = HorizontalWrapMode.Wrap;
            Legende.supportRichText = false; Legende.color = SocleInterface.Couleur("papier"); Afficher(ENTETE);
        }
        void Afficher(string texte) { Legende.text = texte; Legende.rectTransform.sizeDelta = new Vector2(1100, Mathf.Max(160f, Legende.preferredHeight + 8f)); fond.rectTransform.sizeDelta = new Vector2(Mathf.Min(1100f, Legende.preferredWidth) + 16f, Legende.preferredHeight + 8f); }
        void Update() => Pas(Time.realtimeSinceStartupAsDouble);
        void OnDestroy() { foreach (var o in crees) Detruire(o); crees.Clear(); }
        public static Color CouleurDuMaitre(string id) { uint h = 2166136261u; for (int i = 0; i < id.Length; i++) { h ^= id[i]; h *= 16777619u; } return Color.HSVToRGB(TEINTE_MIN + ETENDUE_TEINTE * (h % PAS_DE_TEINTE) / PAS_DE_TEINTE, SATURATION, VALEUR); }
        public void Pas(double t)
        {
            string id = Maison(); if (id != peinte) { Vider(); peinte = id; if (Legende != null) Afficher(ENTETE); Applique?.Invoke(null, null); }
            if (vol != null && vol.IsCompleted) { var fini = vol; vol = null; if (id != null && !fini.IsFaulted && fini.Result.Maison == id) Appliquer(fini.Result); }
            if (vol != null || id == null || t < prochaine || carte == null || carte.PositionSurLaCarte(default, 0f) == null) return;
            var cells = Cellules(); var lire = Lecteur ?? Lire; prochaine = t + PERIODE_S; string maison = id;
            vol = Task.Run(() => { var lus = new List<(long, LectureLieu)>(cells.Count); foreach (long c in cells) lus.Add((c, SansFaute(lire, c))); return new Paquet { Maison = maison, Cellules = lus }; });
        }
        string Maison() { var p = cabinet != null ? cabinet.Partie : null; var m = p != null ? p.Monde : null; var h = p != null ? p.Maison : null; return m == null || !m.Presente || string.IsNullOrEmpty(m.Donnees.MaisonDuJoueur) || h == null || !h.Presente || h.Donnees.Id != m.Donnees.MaisonDuJoueur ? null : h.Donnees.Id; }
        List<long> Cellules() { var vus = new HashSet<long>(); var liste = new List<long>(); foreach (var t in cabinet.Partie.Maison.Donnees.Lieux) if (vus.Add(t.CellId)) liste.Add(t.CellId); return liste; }
        LectureLieu Lire(long cell) { using (var c = new ClientLieu(carte.port, ClientDeparts.DelaiMinimal)) return c.Lire(cell); }
        static LectureLieu SansFaute(Func<long, LectureLieu> lire, long cell) { try { return lire(cell); } catch (Exception e) { return LectureLieu.Absent("lieu " + cell.ToString(CultureInfo.InvariantCulture) + " : " + e.GetBaseException().Message); } }
        void Appliquer(Paquet p)
        {
            var garder = new HashSet<string>(); var sb = new StringBuilder(ENTETE);
            foreach (var (cell, lu) in p.Cellules)
            {
                string c = cell.ToString(CultureInfo.InvariantCulture);
                if (!lu.Presente || lu.Lieu.Lieux == null || lu.Lieu.Lieux.Count == 0) { sb.Append("\nCellule ").Append(c).Append(" : ").Append(!lu.Presente ? lu.Absence : lu.Lieu.Lieux == null ? lu.Lieu.AbsenceDesLieux : "liste vide"); continue; }
                sb.Append("\nCellule ").Append(c).Append(" au tick ").Append(lu.Lieu.Tick.ToString(CultureInfo.InvariantCulture));
                foreach (var lieu in lu.Lieu.Lieux)
                {
                    string r = lieu.Rang.ToString(CultureInfo.InvariantCulture); Vector3? pose = lieu.Position is PointCarte point ? carte.PositionSurLaCarte(point, ReperesDeDepart.HAUTEUR_LIEU) : null;
                    if (pose == null || lieu.Maitre == null) { sb.Append("\nCellule ").Append(c).Append(", rang ").Append(r).Append(" : ").Append(lieu.Position == null || pose == null ? "point absent" : "maître absent"); continue; }
                    bool rouge = lieu.Flux != null && lieu.Flux.PartisPersonnes > lieu.Flux.ArrivesPersonnes;
                    Poser(c + "-" + r, pose.Value, rouge ? ROUGE : lieu.Maitre == p.Maison ? ReperesDeDepart.COULEUR_JOUEUR : CouleurDuMaitre(lieu.Maitre), garder);
                    if (lieu.Flux == null) sb.Append("\nCellule ").Append(c).Append(", rang ").Append(r).Append(" : ").Append(lieu.AbsenceDesFlux);
                }
            }
            if (racine != null) for (int i = racine.childCount - 1; i >= 0; i--) { var e = racine.GetChild(i); if (!garder.Contains(e.name)) Detruire(e.gameObject); }
            Afficher(sb.ToString()); Applique?.Invoke(p.Maison, p.Cellules);
        }
        void Poser(string couple, Vector3 local, Color couleur, HashSet<string> garder)
        {
            if (racine == null) { racine = new GameObject(RACINE).transform; racine.SetParent(transform, false); crees.Add(racine.gameObject); }
            string nom = "Lieu " + couple; garder.Add(nom); var parent = racine.Find(nom);
            if (parent == null) { parent = new GameObject(nom).transform; parent.SetParent(racine, false); Disque(parent, "Bord", Bord(), ReperesDeDepart.DIAMETRE_BORD_KM, ReperesDeDepart.SOUS_LE_DISQUE); Disque(parent, "Disque", Mat(couleur), ReperesDeDepart.DIAMETRE_LIEU_KM, 0f); }
            parent.localPosition = local; parent.Find("Disque").GetComponent<MeshRenderer>().sharedMaterial = Mat(couleur);
        }
        void Disque(Transform parent, string nom, Material mat, float diametre, float haut) { var o = GameObject.CreatePrimitive(PrimitiveType.Cylinder); o.name = nom; Detruire(o.GetComponent<Collider>()); o.GetComponent<MeshRenderer>().sharedMaterial = mat; o.transform.SetParent(parent, false); o.transform.localPosition = new Vector3(0f, haut, 0f); o.transform.localScale = new Vector3(diametre, EPAISSEUR_KM, diametre); }
        Material Mat(Color couleur) { if (!mats.TryGetValue(couleur, out var mat)) { mat = new Material(GraphicsSettings.currentRenderPipeline.defaultMaterial) { color = couleur }; mats.Add(couleur, mat); crees.Add(mat); } return mat; }
        Material Bord() { if (bord == null) { bord = new Material(GraphicsSettings.currentRenderPipeline.defaultMaterial) { color = ReperesDeDepart.BORD_JOUEUR }; crees.Add(bord); } return bord; }
        void Vider() { if (racine == null) return; for (int i = racine.childCount - 1; i >= 0; i--) Detruire(racine.GetChild(i).gameObject); }
        static void Detruire(UnityEngine.Object o) { if (o == null) return; if (Application.isPlaying) UnityEngine.Object.Destroy(o); else DestroyImmediate(o); }
    }
}
