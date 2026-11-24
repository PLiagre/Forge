using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;
using UnityEngine.Rendering;

namespace Forge.Interface
{
    // Les noms de l'atlas sur la carte : les fleuves tracés et nommés, les mers et les régions nommées, en italique, tels que
    // `/atlas` les sert, lus une fois hors du fil principal. Le corps d'un nom suit sa sorte, une mer plus grande qu'une
    // région, une région plus grande qu'un fleuve : la règle des noms (`NomsCourbes`) lit donc de loin les mers, de plus près
    // les régions, et les fleuves de près. Un nom de l'atlas ne s'écrit pas sur un nom de pays lisible, ni sur un nom de
    // l'atlas plus important déjà montré, ni sur le nom d'une capitale ; ceux qu'il montre réservent leur place, et un nom de ville ne s'écrit pas dessus.
    // Rien n'est calculé du monde : les places sont celles servies, et un fleuve se trace d'un point servi au suivant.
    public sealed class AtlasDeCarte : MonoBehaviour
    {
        public const string RACINE = "Atlas de la carte", FLEUVES = "Fleuves de la carte";
        public const string MER = "mer", REGION = "region", FLEUVE = "fleuve";
        // Le corps des noms, en km de la carte, selon leur sorte.
        public const float CORPS_DE_MER_KM = 55f, CORPS_DE_REGION_KM = 26f, CORPS_DE_FLEUVE_KM = 15f;
        // Le trait d'un fleuve : sa largeur en km, jamais sous `MIN_PX` ni au-dessus de `MAX_PX` pixels à l'écran ; sa hauteur au-dessus du sol.
        public const float LARGEUR_DU_FLEUVE_KM = 3f, MIN_PX = 1.4f, MAX_PX = 3.5f, HAUTEUR_DU_FLEUVE = 0.3f;
        // La portion presque droite d'un cours qui porte son nom : aucun de ses points ne s'écarte de sa corde de plus de
        // cette part de sa longueur. Le nom se tient à côté du trait, décalé de `ECART_DU_NOM` corps vers le haut des lettres.
        public const float DROIT = 0.12f, ECART_DU_NOM = 0.75f;
        // Une lecture échouée se retente après ce délai.
        public const double REPRISE_S = 5;
        static readonly TimeSpan DELAI = TimeSpan.FromSeconds(10);

        public Func<Lecture<AtlasLu>> LecteurAtlas;
        public AtlasLu Atlas { get; private set; }
        public string Absence { get; private set; }
        public NomsCourbes Ecriture => ecriture;
        public bool LectureEnVol => vol != null && !vol.IsCompleted;
        // Les noms posés, des mers aux fleuves, et le trait de chaque cours.
        public IReadOnlyList<NomCourbe> Noms => ecriture != null ? ecriture.Noms : (IReadOnlyList<NomCourbe>)new NomCourbe[0];
        public IReadOnlyList<LineRenderer> Traits => traits;
        // La sorte d'un nom posé (`MER`, `REGION` ou `FLEUVE`), et le fleuve d'un trait.
        public string SorteDe(NomCourbe nom) => nom != null && sortes.TryGetValue(nom.Pays, out string sorte) ? sorte : null;
        public string FleuveDuTrait(LineRenderer trait) => trait != null && fleuves.TryGetValue(trait, out string nom) ? nom : null;

        CarteDessinee carte; CarteDeLaGuerre guerre; CalquesCarte calques; NomsCourbes ecriture; Transform racineDesFleuves; Material encreDesFleuves;
        Task<Lecture<AtlasLu>> vol; double reprise; bool dessine;
        readonly List<LineRenderer> traits = new List<LineRenderer>(); readonly Dictionary<string, string> sortes = new Dictionary<string, string>();
        readonly Dictionary<LineRenderer, string> fleuves = new Dictionary<LineRenderer, string>();
        readonly List<Rect> prises = new List<Rect>(), lettres = new List<Rect>();

        public void Installer(CarteDeLaGuerre guerre = null) { carte = GetComponent<CarteDessinee>(); this.guerre = guerre; }
        // Les noms des capitales montrés par les calques : un nom de l'atlas ne s'écrit pas dessus.
        public void Eviter(CalquesCarte calques) { this.calques = calques; }
        void Update() => Pas(Time.realtimeSinceStartupAsDouble);
        void LateUpdate() => SuivreLaVue();
        void OnDestroy()
        {
            ecriture?.Dispose(); ecriture = null;
            if (racineDesFleuves != null) Detruire(racineDesFleuves.gameObject);
            if (encreDesFleuves != null) Detruire(encreDesFleuves);
        }

        // Lit l'atlas une fois, puis le dessine dès que la carte est posée.
        public void Pas(double maintenant)
        {
            if (carte == null) return;
            if (vol != null && vol.IsCompleted)
            {
                var fini = vol; vol = null;
                Lecture<AtlasLu> lu = fini.Status == TaskStatus.RanToCompletion && fini.Result != null ? fini.Result : Lecture<AtlasLu>.Absent("atlas : " + (fini.Exception?.GetBaseException().Message ?? "aucune lecture rendue"));
                if (lu.Presente) { Atlas = lu.Donnees; Absence = null; } else { Absence = lu.Absence; reprise = maintenant + REPRISE_S; }
            }
            if (Atlas == null && vol == null && maintenant >= reprise)
            {
                var lire = LecteurAtlas ?? Lire;
                vol = Task.Run(() => { try { return lire() ?? Lecture<AtlasLu>.Absent("atlas : aucune lecture rendue"); } catch (Exception e) { return Lecture<AtlasLu>.Absent("atlas : " + e.GetBaseException().Message); } });
            }
            if (Atlas != null && !dessine && carte.Terrain != null && carte.PositionSurLaCarte(default, 0f) != null) Dessiner();
        }
        Lecture<AtlasLu> Lire() { using (var c = new ClientAtlas(carte.port, DELAI)) return c.Lire(); }

        void Dessiner()
        {
            dessine = true; sortes.Clear();
            ecriture = new NomsCourbes(transform, SocleInterface.Police(titre: true), SocleInterface.Couleur("encre"), SocleInterface.Couleur("papier"), p => carte.SurLeSol(p.x, p.y, NomsCourbes.HAUTEUR));
            ecriture.Racine.name = RACINE;
            var noms = new List<(string, string, Vector2, Vector2, float, StyleDeNom)>();
            void Nommer(string sorte, string nom, Vector2 centre, Vector2 axe, float corps) { string id = sorte + " " + nom; sortes[id] = sorte; noms.Add((id, nom, centre, axe, corps, StyleDeNom.Italique)); }
            foreach (NomDeLAtlas mer in Atlas.Mers) if (Place(mer.Point) is Vector2 p) Nommer(MER, mer.Nom, p, Vector2.right, CORPS_DE_MER_KM);
            foreach (NomDeLAtlas region in Atlas.Regions) if (Place(region.Point) is Vector2 p) Nommer(REGION, region.Nom, p, Vector2.right, CORPS_DE_REGION_KM);
            racineDesFleuves = new GameObject(FLEUVES).transform; racineDesFleuves.SetParent(transform, false);
            // L'encre des eaux : la mer du socle tirée vers le papier, comme les lignes d'eau du terrain.
            encreDesFleuves = new Material(MateriauDeBase.Prendre()) { name = FLEUVES, color = Color.Lerp(SocleInterface.Couleur("mer"), SocleInterface.Couleur("papier"), .25f) };
            foreach (FleuveDeLAtlas fleuve in Atlas.Fleuves)
            {
                var cours = new List<IReadOnlyList<Vector2>>();
                foreach (var ligne in fleuve.Lignes)
                {
                    var points = ligne.Select(Place).Where(p => p.HasValue).Select(p => p.Value).ToList(); if (points.Count < 2) continue;
                    cours.Add(points); Tracer(fleuve.Nom, points);
                }
                if (PortionDroite(cours) is (Vector2 a, Vector2 b))
                {
                    Vector2 axe = (b - a).normalized; if (axe.x < 0f) axe = -axe;
                    Nommer(FLEUVE, fleuve.Nom, (a + b) / 2f + new Vector2(-axe.y, axe.x) * (ECART_DU_NOM * CORPS_DE_FLEUVE_KM), axe, CORPS_DE_FLEUVE_KM);
                }
            }
            ecriture.Ecrire(noms);
            SuivreLaVue();
        }
        Vector2? Place(PointCarte point) => carte.PositionSurLaCarte(point, 0f) is Vector3 v ? new Vector2(v.x, v.z) : (Vector2?)null;

        // Le trait d'un cours, drapé sur le sol d'un point servi au suivant.
        void Tracer(string nom, List<Vector2> points)
        {
            var trait = new GameObject("Fleuve " + nom).AddComponent<LineRenderer>(); trait.transform.SetParent(racineDesFleuves, false);
            trait.useWorldSpace = false; trait.shadowCastingMode = ShadowCastingMode.Off; trait.receiveShadows = false; trait.sharedMaterial = encreDesFleuves; trait.numCapVertices = 2;
            var draps = new List<Vector3> { carte.SurLeSol(points[0].x, points[0].y, HAUTEUR_DU_FLEUVE) };
            for (int k = 1; k < points.Count; k++)
            {
                List<Vector3> troncon = carte.Draper(carte.SurLeSol(points[k - 1].x, points[k - 1].y, HAUTEUR_DU_FLEUVE), carte.SurLeSol(points[k].x, points[k].y, HAUTEUR_DU_FLEUVE), HAUTEUR_DU_FLEUVE);
                for (int j = 1; j < troncon.Count; j++) draps.Add(troncon[j]);
            }
            trait.positionCount = draps.Count; trait.SetPositions(draps.ToArray()); trait.widthMultiplier = LARGEUR_DU_FLEUVE_KM; traits.Add(trait); fleuves[trait] = nom;
        }

        // La plus longue corde d'un cours dont aucun point intermédiaire ne s'écarte de plus de `DROIT` de sa longueur ; null pour un cours vide.
        public static (Vector2, Vector2)? PortionDroite(IEnumerable<IReadOnlyList<Vector2>> cours)
        {
            (Vector2, Vector2)? meilleure = null; float longueur = 0f;
            foreach (var points in cours)
                for (int i = 0; i < points.Count; i++)
                    for (int j = i + 1; j < points.Count; j++)
                    {
                        Vector2 a = points[i], b = points[j]; float corde = (b - a).magnitude; if (corde <= longueur) continue;
                        bool droite = true; Vector2 sens = (b - a) / corde;
                        for (int k = i + 1; k < j && droite; k++) { Vector2 d = points[k] - a; droite = Mathf.Abs(d.x * sens.y - d.y * sens.x) <= DROIT * corde; }
                        if (droite) { meilleure = (a, b); longueur = corde; }
                    }
            return meilleure;
        }

        // Règle les traits et les noms sur la vue : un nom qui tomberait sur un nom de pays lisible, sur une capitale nommée, ou sur un nom plus
        // important déjà montré se masque, des mers aux fleuves. Les places sont celles de l'image d'avant.
        public void SuivreLaVue()
        {
            if (ecriture == null || carte == null || carte.camera == null) return;
            Camera camera = carte.camera;
            foreach (LineRenderer trait in traits)
            {
                if (trait == null || trait.positionCount == 0) continue;
                float kmParPixel = FormesDeCarte.KmParPixel(camera, trait.transform.TransformPoint(trait.GetPosition(0)));
                trait.widthMultiplier = kmParPixel > 0f ? Mathf.Clamp(LARGEUR_DU_FLEUVE_KM, MIN_PX * kmParPixel, MAX_PX * kmParPixel) : LARGEUR_DU_FLEUVE_KM;
            }
            prises.Clear(); guerre?.Ecriture?.Reserver(camera, prises); if (calques != null) prises.AddRange(calques.PlacesDesCapitales);
            foreach (NomCourbe nom in ecriture.Noms)
            {
                lettres.Clear(); ecriture.Places(camera, nom, lettres);
                bool masque = false;
                foreach (Rect l in lettres) { foreach (Rect p in prises) if (l.Overlaps(p)) { masque = true; break; } if (masque) break; }
                nom.Masque = masque;
                if (!masque && NomsCourbes.Opacite(nom.CorpsPx, camera.pixelHeight) >= NomsCourbes.OPACITE_QUI_RESERVE) prises.AddRange(lettres);
            }
            ecriture.Suivre(camera);
        }

        static void Detruire(UnityEngine.Object o) { if (o == null) return; if (Application.isPlaying) Destroy(o); else DestroyImmediate(o); }
    }
}
