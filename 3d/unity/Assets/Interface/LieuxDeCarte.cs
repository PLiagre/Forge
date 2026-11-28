using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;
namespace Forge.Interface
{
    // Lecture des lieux des cellules tenues par le joueur, hors du fil principal : chaque lieu a déjà sa forme et la couleur de son pays sur le terrain.
    // `EnAlerte` dit quels lieux du joueur voient partir plus de gens qu'il n'en arrive sur trente jours, en couples (cellule, rang) triés ;
    // `VersionDesAlertes` change quand cet ensemble change, et seulement alors, pour que la carte ne repeigne qu'à ce moment. `TexteLegende` relève ce qui manque.
    // Chaque lieu en alerte porte une marque (`FormesDeCarte.Depart`) : une flèche d'encre bordée de papier, posée à la place que le monde sert au lieu,
    // jamais plus petite que `MIN_PX` pixels ; elle ne se montre que sur la carte politique (`MontrerLesMarques`). Aucune teinte ne dit l'alerte. Lecture seule.
    public sealed class LieuxDeCarte : MonoBehaviour
    {
        public const string ENTETE = "Flèche d'encre : vos lieux d'où partent plus de gens qu'il n'en arrive, sur trente jours."; public const float PERIODE_S = 2f;
        public const string MARQUES = "Marques des départs"; public const float MIN_PX = 18f, HAUTEUR_DE_LA_MARQUE = 0.9f, LONGUEUR_DE_LA_MARQUE_KM = 1f;
        // Les marques posées, une par lieu en alerte, en (cellule, rang) ; et si elles se montrent.
        public IReadOnlyDictionary<(long cell, long rang), Transform> Marques => marques;
        public bool MarquesMontrees { get; private set; } = true;
        readonly Dictionary<(long, long), Transform> marques = new Dictionary<(long, long), Transform>(); Transform racineDesMarques; Mesh formeDesMarques; Material matiereDesMarques;
        public Func<long, LectureLieu> Lecteur;
        public string TexteLegende { get; private set; } public bool Peint => peinte != null; // lus par la légende du mode Politique et son infobulle ; peint, une maison du joueur est lue
        public bool LectureEnVol => vol != null && !vol.IsCompleted;
        public IReadOnlyList<(long cell, long rang)> EnAlerte { get; private set; } = new (long, long)[0]; public int VersionDesAlertes { get; private set; } // vide quand la maison change ou se vide
        public event Action<string, IReadOnlyList<(long cell, LectureLieu lieu)>> Applique; // la maison et la réponse appliquée ; maison nulle quand l'ancien domaine est vidé
        CarteDessinee carte; CabinetDeCarte cabinet; Task<Paquet> vol; double prochaine; string peinte;
        sealed class Paquet { public string Maison; public List<(long cell, LectureLieu lieu)> Cellules; }
        public void Installer() { carte = GetComponent<CarteDessinee>(); cabinet = GetComponent<CabinetDeCarte>(); TexteLegende = ENTETE; }
        // Une marque se pose à la place servie de son lieu, petite au ras du sol : elle n'a rien à éviter.
        public void Eviter(CarteDeLaGuerre guerre, CalquesCarte calques) { }
        void Update() => Pas(Time.realtimeSinceStartupAsDouble);
        void LateUpdate() => SuivreLaVue();
        void OnDestroy() { if (racineDesMarques != null) Detruire(racineDesMarques.gameObject); if (formeDesMarques != null) Detruire(formeDesMarques); if (matiereDesMarques != null) Detruire(matiereDesMarques); marques.Clear(); }
        // Les marques des départs se montrent, ou se cachent hors de la carte politique.
        public void MontrerLesMarques(bool montrees) { MarquesMontrees = montrees; if (racineDesMarques != null) racineDesMarques.gameObject.SetActive(montrees); }
        // Chaque marque garde au moins `MIN_PX` pixels à l'écran, là où elle est.
        public void SuivreLaVue()
        {
            Camera camera = carte != null ? carte.camera : null; if (camera == null) return;
            foreach (Transform marque in marques.Values) marque.localScale = Vector3.one * LONGUEUR_DE_LA_MARQUE_KM * FormesDeCarte.EchellePourLEcran(camera, marque.position, LONGUEUR_DE_LA_MARQUE_KM / 2f, MIN_PX);
        }
        // Une marque par lieu en alerte, à sa place servie ; celles des lieux qui ne le sont plus partent.
        void Marquer(List<(long cell, long rang, Vector3 ici)> enAlerte)
        {
            var garder = new HashSet<(long, long)>();
            foreach (var (cell, rang, ici) in enAlerte)
            {
                garder.Add((cell, rang));
                if (!marques.TryGetValue((cell, rang), out Transform marque))
                {
                    if (racineDesMarques == null) { racineDesMarques = new GameObject(MARQUES).transform; racineDesMarques.SetParent(carte.transform, false); racineDesMarques.gameObject.SetActive(MarquesMontrees); }
                    if (formeDesMarques == null) { formeDesMarques = FormesDeCarte.Depart(SocleInterface.Couleur("encre"), SocleInterface.Couleur("papier")); matiereDesMarques = FormesDeCarte.Matiere(SocleInterface.Couleur("encre")); }
                    var objet = new GameObject("Marque " + cell.ToString(CultureInfo.InvariantCulture) + "-" + rang.ToString(CultureInfo.InvariantCulture), typeof(MeshFilter), typeof(MeshRenderer));
                    objet.transform.SetParent(racineDesMarques, false); objet.GetComponent<MeshFilter>().sharedMesh = formeDesMarques;
                    var rendu = objet.GetComponent<MeshRenderer>(); rendu.sharedMaterial = matiereDesMarques; rendu.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; rendu.receiveShadows = false;
                    marque = objet.transform; marques[(cell, rang)] = marque;
                }
                marque.localPosition = ici;
            }
            foreach (var cle in marques.Keys.Where(c => !garder.Contains(c)).ToList()) { Detruire(marques[cle].gameObject); marques.Remove(cle); }
            SuivreLaVue();
        }
        static void Detruire(UnityEngine.Object o) { if (o == null) return; if (Application.isPlaying) Destroy(o); else DestroyImmediate(o); }
        // Une terre se nomme par son bourg (le rang 0 servi), un lieu par son nom servi ; l'absence se dit, jamais un numéro.
        public static string Bourg(Lieu lieu) { var b = lieu.Bourg; return b?.Nom ?? "Bourg sans nom (" + TexteDuMonde.Absence(b == null ? "bourg non servi" : b.AbsenceDuNom, Cle(lieu)) + ")"; }
        public static string Tenue(Lieu lieu, LieuPlace place) => place.Rang == 0 ? Bourg(lieu) : Bourg(lieu) + " · " + (place.Nom ?? "lieu sans nom (" + TexteDuMonde.Absence(place.AbsenceDuNom, Cle(lieu)) + ")");
        static string Cle(Lieu lieu) => lieu.CellId.ToString(CultureInfo.InvariantCulture);
        public void Pas(double t)
        {
            string id = Maison(); if (id != peinte) { Alerter(new List<(long, long)>()); if (marques.Count > 0) Marquer(new List<(long, long, Vector3)>()); peinte = id; TexteLegende = ENTETE; Applique?.Invoke(null, null); }
            if (vol != null && vol.IsCompleted) { var fini = vol; vol = null; if (id != null && !fini.IsFaulted && fini.Result.Maison == id) Appliquer(fini.Result); }
            if (vol != null || id == null || t < prochaine || carte == null || carte.PositionSurLaCarte(default, 0f) == null) return;
            var cells = Cellules(); var lire = Lecteur ?? Lire; prochaine = t + PERIODE_S; string maison = id;
            vol = Task.Run(() => { var lus = new List<(long, LectureLieu)>(cells.Count); foreach (long c in cells) lus.Add((c, SansFaute(lire, c))); return new Paquet { Maison = maison, Cellules = lus }; });
        }
        string Maison() { var p = cabinet != null ? cabinet.Partie : null; var m = p != null ? p.Monde : null; var h = p != null ? p.Maison : null; return m == null || !m.Presente || string.IsNullOrEmpty(m.Donnees.MaisonDuJoueur) || h == null || !h.Presente || h.Donnees.Id != m.Donnees.MaisonDuJoueur ? null : h.Donnees.Id; }
        List<long> Cellules() { var vus = new HashSet<long>(); var liste = new List<long>(); foreach (var t in cabinet.Partie.Maison.Donnees.Lieux) if (vus.Add(t.CellId)) liste.Add(t.CellId); return liste; }
        LectureLieu Lire(long cell) { using (var c = new ClientLieu(carte.port, ClientDeparts.DelaiMinimal)) return c.Lire(cell); }
        static LectureLieu SansFaute(Func<long, LectureLieu> lire, long cell) { try { return lire(cell); } catch (Exception e) { return LectureLieu.Absent("lieu " + cell.ToString(CultureInfo.InvariantCulture) + " : " + e.GetBaseException().Message); } }
        // Un lieu sans flux servi n'est pas en alerte : son absence se dit dans le relevé.
        void Appliquer(Paquet p)
        {
            var sb = new StringBuilder(ENTETE); var alertes = new List<(long cell, long rang)>(); var places = new List<(long, long, Vector3)>();
            foreach (var (cell, lu) in p.Cellules)
            {
                string c = cell.ToString(CultureInfo.InvariantCulture);
                if (!lu.Presente || lu.Lieu.Lieux == null || lu.Lieu.Lieux.Count == 0) { sb.Append("\nTerre sans lieux lus : ").Append(TexteDuMonde.Absence(!lu.Presente ? lu.Absence : lu.Lieu.Lieux == null ? lu.Lieu.AbsenceDesLieux ?? "lieux non servis" : "liste vide", c)); continue; }
                sb.Append('\n').Append(Bourg(lu.Lieu)).Append(" · relevé au ").Append(TexteDuMonde.Date(new DateDuMonde(lu.Lieu.Annee, lu.Lieu.JourDeLAnnee)));
                foreach (var lieu in lu.Lieu.Lieux)
                {
                    bool enAlerte = lieu.Maitre == p.Maison && lieu.Flux != null && lieu.Flux.PartisPersonnes > lieu.Flux.ArrivesPersonnes;
                    if (enAlerte) alertes.Add((cell, lieu.Rang));
                    Vector3? pose = lieu.Position is PointCarte point ? carte.PositionSurLaCarte(point, 0f) : null;
                    if (enAlerte && lieu.Position is PointCarte place && carte.PositionSurLaCarte(place, HAUTEUR_DE_LA_MARQUE) is Vector3 ici) places.Add((cell, lieu.Rang, ici));
                    if (pose == null || lieu.Maitre == null) { sb.Append('\n').Append(Tenue(lu.Lieu, lieu)).Append(pose == null ? " : point absent" : " : maître absent"); continue; }
                    if (lieu.Flux == null) sb.Append('\n').Append(Tenue(lu.Lieu, lieu)).Append(" : ").Append(TexteDuMonde.Absence(lieu.AbsenceDesFlux ?? "flux non servis", c));
                }
            }
            Alerter(alertes); Marquer(places); TexteLegende = sb.ToString(); Applique?.Invoke(p.Maison, p.Cellules);
        }
        // L'ensemble trié des lieux en alerte ; sa version ne bouge que s'il a changé.
        void Alerter(List<(long cell, long rang)> alertes)
        {
            alertes.Sort(); if (alertes.SequenceEqual(EnAlerte)) return;
            EnAlerte = alertes; VersionDesAlertes++;
        }
    }
}
