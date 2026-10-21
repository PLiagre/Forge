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
    // Lot #658 : ce que chaque lieu tenu a envoyé à son siège, et le dû du siège au suzerain, sur trente jours. Lecture seule : aucun kilo calculé.
    public sealed class FlechesDeCarte : MonoBehaviour
    {
        public const string RACINE = "Flèches de la carte", DU = "Flèche du dû", ENTETE = "Orange : du lieu vers votre siège, ce qui en a été prélevé. Violet : de votre siège vers celui du suzerain, le dû envoyé. Sur trente jours ; 1 km de large pour 50 000 kg, plafond 8 km.";
        public const float KG_PAR_KM = 50000f, EPAISSEUR_MAX_KM = 8f, PERIODE_S = 2f, HAUTEUR = 0.56f; // entre les contours (0,5) et le bord des disques (0,63)
        public static readonly Color ORANGE = Color.HSVToRGB(0.08f, 0.9f, 0.95f), VIOLET = Color.HSVToRGB(0.8f, 0.9f, 0.7f);
        static readonly CultureInfo Fr = CultureInfo.GetCultureInfo("fr-FR"), Inv = CultureInfo.InvariantCulture;
        public static float Epaisseur(double kg) => (float)Math.Min(EPAISSEUR_MAX_KM, kg / KG_PAR_KM);
        public static string Kg(double kg) => kg.ToString("N0", Fr) + " kg";
        public Func<string, Lecture<ComptesDeMaison>> Lecteur; public Text Legende { get; private set; }
        public string TexteLegende => Legende != null ? Legende.text : null;
        public bool LectureEnVol => vol != null && !vol.IsCompleted;
        CarteDessinee carte; CabinetDeCarte cabinet; LieuxDeCarte lieux; Transform racine; Image fond; string lignesLieux = "", ligneDu = "", duDe;
        readonly Dictionary<Color, Material> mats = new Dictionary<Color, Material>();
        Task<(string maison, Lecture<ComptesDeMaison> joueur, Lecture<ComptesDeMaison> suzerain)> vol; double prochaine;
        public void Installer(Transform toile, LieuxDeCarte vue)
        {
            carte = GetComponent<CarteDessinee>(); cabinet = GetComponent<CabinetDeCarte>(); lieux = vue; lieux.Applique += Lieux;
            // Dans la bande de carte entre le feuillet (x ≤ 764) et le fond des dossiers (x ≥ 1286), posée sur « Parcourir le monde » (y ≥ 872) ; elle ne prend pas les clics.
            fond = new GameObject("Fond des flèches", typeof(Image)).GetComponent<Image>(); var f = fond.rectTransform; f.SetParent(toile, false); f.anchorMin = f.anchorMax = f.pivot = Vector2.zero; f.anchoredPosition = new Vector2(776, 216); fond.raycastTarget = false; fond.color = SocleInterface.Couleur("fond") * new Color(1f, 1f, 1f, 0.72f);
            Legende = SocleInterface.Texte(fond.transform, "Légende des flèches", 8, 4, 480, 16); Legende.alignment = TextAnchor.UpperLeft; Legende.horizontalOverflow = HorizontalWrapMode.Wrap; Legende.supportRichText = false; Legende.color = SocleInterface.Couleur("papier"); Afficher();
        }
        void Afficher() { Legende.text = ENTETE + lignesLieux + ligneDu; float h = Legende.preferredHeight; Legende.rectTransform.sizeDelta = new Vector2(480, h + 4f); fond.rectTransform.sizeDelta = new Vector2(496, h + 12f); }
        void Update() { if (Legende != null && Mathf.Abs(Legende.preferredHeight + 4f - Legende.rectTransform.rect.height) > 1f) Afficher(); Pas(Time.realtimeSinceStartupAsDouble); } // la toile peut changer d'échelle
        void OnDestroy() { if (lieux != null) lieux.Applique -= Lieux; Retirer(_ => true); if (racine != null) Detruire(racine.gameObject); foreach (var m in mats.Values) Detruire(m); mats.Clear(); }
        // Les flèches des lieux suivent la réponse que les disques viennent d'appliquer : même lecture, même tick.
        void Lieux(string maison, IReadOnlyList<(long cell, LectureLieu lieu)> lus)
        {
            var garder = new HashSet<string> { DU }; var sb = new StringBuilder(); var h = cabinet != null && cabinet.Partie != null ? cabinet.Partie.Maison : null;
            var siege = maison != null && h != null && h.Presente && h.Donnees.Id == maison ? h.Donnees.Siege : null; Vector3? cible = siege != null && siege.Position is PointCarte ps ? carte.PositionSurLaCarte(ps, HAUTEUR) : null;
            if (maison != null && cible == null) sb.Append("\nAucune flèche vers le siège : ").Append(siege == null ? "maison non lue" : "siège hors carte" + Raison(h.Donnees));
            else if (maison != null) foreach (var (cell, lu) in lus) if (lu.Presente && lu.Lieu.Lieux != null) foreach (var l in lu.Lieu.Lieux)
            {
                if (l.Maitre != maison) continue; string c = cell.ToString(Inv) + "-" + l.Rang.ToString(Inv);
                if (cell == siege.CellId && l.Rang == siege.Rang) { sb.Append('\n').Append(siege.Nom).Append(" : ").Append(l.Flux != null ? Kg(l.Flux.PreleveKg) + " prélevés sur place, sans flèche" : l.AbsenceDesFlux); continue; }
                Vector3? source = l.Position is PointCarte p ? carte.PositionSurLaCarte(p, HAUTEUR) : null; sb.Append("\nLieu ").Append(c).Append(" → ").Append(siege.Nom).Append(" : ");
                if (l.Flux == null || source == null) sb.Append(l.Flux == null ? l.AbsenceDesFlux : "point absent"); else sb.Append(Kg(l.Flux.PreleveKg)).Append(Fleche("Flèche " + c, source.Value, cible.Value, l.Flux.PreleveKg, ORANGE, garder));
            }
            Retirer(n => !garder.Contains(n)); lignesLieux = sb.ToString(); if (Legende != null) Afficher();
        }
        // Le dû a sa propre lecture, hors du fil principal : les comptes du joueur, puis ceux de son suzerain pour son siège.
        public void Pas(double t)
        {
            string id = Maison(); if (id != duDe) { duDe = id; Retirer(n => n == DU); ligneDu = ""; if (Legende != null) Afficher(); }
            if (vol != null && vol.IsCompleted) { var fini = vol; vol = null; if (id != null && !fini.IsFaulted && fini.Result.maison == id) Du(fini.Result.joueur, fini.Result.suzerain); }
            if (vol != null || id == null || t < prochaine || carte == null || carte.PositionSurLaCarte(default, 0f) == null) return;
            var lire = Lecteur ?? Lire; prochaine = t + PERIODE_S; string maison = id;
            vol = Task.Run(() => { var j = SansFaute(lire, maison); return (maison, j, j.Presente && j.Donnees.Suzerain != null ? SansFaute(lire, j.Donnees.Suzerain) : null); });
        }
        void Du(Lecture<ComptesDeMaison> j, Lecture<ComptesDeMaison> s)
        {
            var garder = new HashSet<string>(); var siege = j.Presente ? j.Donnees.Maison.Siege : null; var haut = s != null && s.Presente ? s.Donnees.Maison.Siege : null; string cause = null;
            Vector3? a = siege?.Position is PointCarte pa ? carte.PositionSurLaCarte(pa, HAUTEUR) : null, b = haut?.Position is PointCarte pb ? carte.PositionSurLaCarte(pb, HAUTEUR) : null;
            if (!j.Presente) cause = "lecture refusée : " + j.Absence; else if (j.Donnees.Suzerain == null) cause = "sans suzerain : aucun dû"; else if (!s.Presente) cause = "suzerain " + j.Donnees.Suzerain + " : " + s.Absence;
            else if (a == null) cause = "votre siège hors carte" + Raison(j.Donnees.Maison); else if (b == null) cause = "siège du suzerain hors carte" + Raison(s.Donnees.Maison);
            ligneDu = cause != null ? "\nDû au suzerain : " + cause : "\n" + siege.Nom + " → " + haut.Nom + " : " + Kg(j.Donnees.Flux.DuEnvoyeKg) + " de dû" + Fleche(DU, a.Value, b.Value, j.Donnees.Flux.DuEnvoyeKg, VIOLET, garder);
            Retirer(n => n == DU && !garder.Contains(n)); if (Legende != null) Afficher();
        }
        static string Raison(MaisonLue m) => m.Absents.TryGetValue("siege", out var r) ? " : " + r : "";
        // Une hampe large de l'épaisseur, une pointe de deux épaisseurs sur trois de long (au plus la moitié de la flèche), d'un bord de disque à l'autre.
        string Fleche(string nom, Vector3 a, Vector3 b, double kg, Color couleur, HashSet<string> garder)
        {
            float w = Epaisseur(kg), r = ReperesDeDepart.DIAMETRE_BORD_KM / 2f; if (Vector3.Distance(a, b) <= 2f * r) return " (les disques se touchent : pas de flèche)"; if (!(w > 0f)) return "";
            if (racine == null) { racine = new GameObject(RACINE).transform; racine.SetParent(transform, false); }
            garder.Add(nom); var o = racine.Find(nom); if (o == null) { o = new GameObject(nom, typeof(MeshFilter), typeof(MeshRenderer)).transform; o.SetParent(racine, false); o.GetComponent<MeshFilter>().sharedMesh = new Mesh { name = nom }; }
            o.GetComponent<MeshRenderer>().sharedMaterial = Mat(couleur); Vector3 u = (b - a).normalized, p = new Vector3(u.z, 0f, -u.x) * (w / 2f), s = a + u * r, t = b - u * r, e = t - u * Mathf.Min(3f * w, Vector3.Distance(s, t) / 2f);
            var m = o.GetComponent<MeshFilter>().sharedMesh; m.Clear(); m.vertices = new[] { s - p, e - p, e + p, s + p, e - 2f * p, t, e + 2f * p }; m.triangles = new[] { 0, 1, 2, 0, 2, 3, 4, 5, 6 }; m.RecalculateNormals(); m.RecalculateBounds(); return "";
        }
        void Retirer(Func<string, bool> quoi) { if (racine == null) return; for (int i = racine.childCount - 1; i >= 0; i--) { var e = racine.GetChild(i); if (quoi(e.name)) { Detruire(e.GetComponent<MeshFilter>().sharedMesh); Detruire(e.gameObject); } } }
        string Maison() { var p = cabinet != null ? cabinet.Partie : null; var m = p != null ? p.Monde : null; var h = p != null ? p.Maison : null; return m == null || !m.Presente || string.IsNullOrEmpty(m.Donnees.MaisonDuJoueur) || h == null || !h.Presente || h.Donnees.Id != m.Donnees.MaisonDuJoueur ? null : h.Donnees.Id; }
        Lecture<ComptesDeMaison> Lire(string id) { using (var c = new ClientMaison(carte.port, ClientDeparts.DelaiMinimal)) return c.LireComptes(id); }
        static Lecture<ComptesDeMaison> SansFaute(Func<string, Lecture<ComptesDeMaison>> lire, string id) { try { return lire(id) ?? Lecture<ComptesDeMaison>.Absent("maison " + id + " : aucune réponse"); } catch (Exception e) { return Lecture<ComptesDeMaison>.Absent("maison " + id + " : " + e.GetBaseException().Message); } }
        Material Mat(Color couleur) { if (!mats.TryGetValue(couleur, out var mat)) { mat = new Material(GraphicsSettings.currentRenderPipeline.defaultMaterial) { color = couleur }; mats.Add(couleur, mat); } return mat; }
        static void Detruire(UnityEngine.Object o) { if (o == null) return; if (Application.isPlaying) UnityEngine.Object.Destroy(o); else DestroyImmediate(o); }
    }
}
