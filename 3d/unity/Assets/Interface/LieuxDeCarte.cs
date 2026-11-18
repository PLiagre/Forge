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
    // Lieux des cellules tenues, couleur du maître, rouge si les départs dépassent les arrivées. Lecture seule.
    // Chaque lieu est une figurine posée sur le sol : un bourg pour le rang 0 de sa terre, un hameau pour les autres ;
    // le dessus de son socle porte la couleur, comme le disque qu'il remplace, sous des maisons aux toits de cuivre. De loin, une figurine ne descend jamais sous `MIN_PX` pixels de large.
    public sealed class LieuxDeCarte : MonoBehaviour
    {
        public const string RACINE = "Lieux de la carte", ENTETE = "Blanc : vos lieux. Couleurs : autres maîtres. Rouge : départs supérieurs aux arrivées sur trente jours.";
        public const string FIGURINE = "Figurine"; public const float PERIODE_S = 2f, MIN_PX = 26f; public const int BOURG = 1, HAMEAU = 0; public static readonly Color ROUGE = new Color(0.86f, 0.05f, 0.04f); // « alerte » (#8B342E) rend un rose terne sur la carte éclairée
        const float TEINTE_MIN = 0.18f, ETENDUE_TEINTE = 0.5f, SATURATION = 0.7f, VALEUR = 0.75f; const uint PAS_DE_TEINTE = 500; // du jaune au bleu : ni blanc ni rouge
        public Func<long, LectureLieu> Lecteur;
        public string TexteLegende { get; private set; } public bool Peint => peinte != null; // lus par la légende du mode Puissances et son infobulle ; peint, une maison du joueur est lue et ses lieux se peignent
        public bool LectureEnVol => vol != null && !vol.IsCompleted;
        public event Action<string, IReadOnlyList<(long cell, LectureLieu lieu)>> Applique; // la maison et la réponse appliquée ; maison nulle quand l'ancien domaine est vidé
        CarteDessinee carte; CabinetDeCarte cabinet; Transform racine; readonly Mesh[] formes = new Mesh[2];
        readonly Dictionary<Color, Material> mats = new Dictionary<Color, Material>();
        readonly List<UnityEngine.Object> crees = new List<UnityEngine.Object>();
        Task<Paquet> vol; double prochaine; string peinte;
        sealed class Paquet { public string Maison; public List<(long cell, LectureLieu lieu)> Cellules; }
        public void Installer() { carte = GetComponent<CarteDessinee>(); cabinet = GetComponent<CabinetDeCarte>(); TexteLegende = ENTETE; }
        void Update() => Pas(Time.realtimeSinceStartupAsDouble);
        void LateUpdate() => SuivreLaVue();
        void OnDestroy() { foreach (var o in crees) Detruire(o); crees.Clear(); }
        // La taille de la figurine d'un lieu : un bourg au rang 0 de sa terre, un hameau ailleurs.
        public static int Taille(long rang) => rang == 0 ? BOURG : HAMEAU;
        // Chaque figurine se règle sur la vue : jamais sous `MIN_PX` pixels de large.
        public void SuivreLaVue()
        {
            if (racine == null || carte == null || carte.camera == null) return;
            foreach (Transform lieu in racine) { var figurine = lieu.Find(FIGURINE); if (figurine == null) continue; float rayon = FormesDeCarte.RayonDuBourg(figurine.GetComponent<MeshFilter>().sharedMesh == formes[BOURG] ? BOURG : HAMEAU); figurine.localScale = Vector3.one * FormesDeCarte.EchellePourLEcran(carte.camera, lieu.position, rayon, MIN_PX); }
        }
        // Une terre se nomme par son bourg (le rang 0 servi), un lieu par son nom servi ; l'absence se dit, jamais un numéro.
        public static string Bourg(Lieu lieu) { var b = lieu.Bourg; return b?.Nom ?? "Bourg sans nom (" + TexteDuMonde.Absence(b == null ? "bourg non servi" : b.AbsenceDuNom, Cle(lieu)) + ")"; }
        public static string Tenue(Lieu lieu, LieuPlace place) => place.Rang == 0 ? Bourg(lieu) : Bourg(lieu) + " · " + (place.Nom ?? "lieu sans nom (" + TexteDuMonde.Absence(place.AbsenceDuNom, Cle(lieu)) + ")");
        static string Cle(Lieu lieu) => lieu.CellId.ToString(CultureInfo.InvariantCulture);
        public static Color CouleurDuMaitre(string id) { uint h = 2166136261u; for (int i = 0; i < id.Length; i++) { h ^= id[i]; h *= 16777619u; } return Color.HSVToRGB(TEINTE_MIN + ETENDUE_TEINTE * (h % PAS_DE_TEINTE) / PAS_DE_TEINTE, SATURATION, VALEUR); }
        public void Pas(double t)
        {
            string id = Maison(); if (id != peinte) { Vider(); peinte = id; TexteLegende = ENTETE; Applique?.Invoke(null, null); }
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
                if (!lu.Presente || lu.Lieu.Lieux == null || lu.Lieu.Lieux.Count == 0) { sb.Append("\nTerre sans lieux lus : ").Append(TexteDuMonde.Absence(!lu.Presente ? lu.Absence : lu.Lieu.Lieux == null ? lu.Lieu.AbsenceDesLieux ?? "lieux non servis" : "liste vide", c)); continue; }
                sb.Append('\n').Append(Bourg(lu.Lieu)).Append(" · relevé au ").Append(TexteDuMonde.Date(new DateDuMonde(lu.Lieu.Annee, lu.Lieu.JourDeLAnnee)));
                foreach (var lieu in lu.Lieu.Lieux)
                {
                    string r = lieu.Rang.ToString(CultureInfo.InvariantCulture); Vector3? pose = lieu.Position is PointCarte point ? carte.PositionSurLaCarte(point, 0f) : null;
                    if (pose == null || lieu.Maitre == null) { sb.Append('\n').Append(Tenue(lu.Lieu, lieu)).Append(pose == null ? " : point absent" : " : maître absent"); continue; }
                    bool rouge = lieu.Flux != null && lieu.Flux.PartisPersonnes > lieu.Flux.ArrivesPersonnes;
                    Poser(c + "-" + r, lieu.Rang, pose.Value, rouge ? ROUGE : lieu.Maitre == p.Maison ? ReperesDeDepart.COULEUR_JOUEUR : CouleurDuMaitre(lieu.Maitre), garder);
                    if (lieu.Flux == null) sb.Append('\n').Append(Tenue(lu.Lieu, lieu)).Append(" : ").Append(TexteDuMonde.Absence(lieu.AbsenceDesFlux ?? "flux non servis", c));
                }
            }
            if (racine != null) for (int i = racine.childCount - 1; i >= 0; i--) { var e = racine.GetChild(i); if (!garder.Contains(e.name)) Detruire(e.gameObject); }
            TexteLegende = sb.ToString(); Applique?.Invoke(p.Maison, p.Cellules);
        }
        void Poser(string couple, long rang, Vector3 local, Color couleur, HashSet<string> garder)
        {
            if (racine == null) { racine = new GameObject(RACINE).transform; racine.SetParent(transform, false); crees.Add(racine.gameObject); }
            string nom = "Lieu " + couple; garder.Add(nom); var parent = racine.Find(nom);
            if (parent == null)
            {
                parent = new GameObject(nom).transform; parent.SetParent(racine, false);
                var figurine = new GameObject(FIGURINE, typeof(MeshFilter), typeof(MeshRenderer)); figurine.transform.SetParent(parent, false);
                var rendu = figurine.GetComponent<MeshRenderer>(); rendu.shadowCastingMode = ShadowCastingMode.Off; rendu.receiveShadows = false;
            }
            parent.localPosition = local; var forme = parent.Find(FIGURINE);
            forme.GetComponent<MeshFilter>().sharedMesh = Forme(Taille(rang)); forme.GetComponent<MeshRenderer>().sharedMaterial = Mat(couleur);
        }
        Mesh Forme(int taille) { if (formes[taille] == null) { formes[taille] = FormesDeCarte.Bourg(taille, SocleInterface.Couleur("papier"), SocleInterface.Couleur("encre"), SocleInterface.Couleur("cuivre"), null); crees.Add(formes[taille]); } return formes[taille]; }
        Material Mat(Color couleur) { if (!mats.TryGetValue(couleur, out var mat)) { mat = FormesDeCarte.Matiere(couleur); mats.Add(couleur, mat); crees.Add(mat); } return mat; }
        void Vider() { if (racine == null) return; for (int i = racine.childCount - 1; i >= 0; i--) Detruire(racine.GetChild(i).gameObject); }
        static void Detruire(UnityEngine.Object o) { if (o == null) return; if (Application.isPlaying) UnityEngine.Object.Destroy(o); else DestroyImmediate(o); }
    }
}
