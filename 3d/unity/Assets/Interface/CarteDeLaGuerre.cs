using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;
using UnityEngine.Rendering;

namespace Forge.Interface
{
    // La guerre sur la carte : le pays de chaque terre (que les calques peignent, et dont le terrain trace la frontière),
    // le nom de chaque pays, couché sur le grand axe de sa terre (`NomsCourbes`), et les armées avec leur nombre et leur route. Tout vient de `/terres` et `/guerres`, lus hors du
    // fil principal toutes les PERIODE_S ; ici ne se fait que le dessin : aucun nombre du monde n'est calculé. Une absence se
    // dit dans la légende.
    public sealed class CarteDeLaGuerre : MonoBehaviour
    {
        public const string NOMS = "Noms des pays", ARMEES = "Armées de la carte", FIGURINE = "Figurine";
        public const string ENTETE = "Traits sombres bordés de la couleur de chaque pays : les frontières entre pays, chacun nommé sur sa terre. Bannières : les armées, à la couleur de leur pays, avec leurs hommes et, en cuivre, leur route ; des piquiers en marche, des tentes au siège.";
        public const float PERIODE_S = 2f;
        // Au-dessus du sol, là où chaque chose se pose : les routes au-dessus des flèches (0,56) ; les armées sur le sol ; leurs
        // nombres au-dessus des villes (1). Une armée ne descend jamais sous `MIN_PX` pixels de large à l'écran, et son nombre
        // se range au sud d'elle, à `MARGE_DU_NOMBRE_PX` pixels de son socle.
        public const float HAUTEUR_ROUTE = 0.58f, HAUTEUR_ARMEE = 0f, HAUTEUR_NOM = 1.1f;
        public const float LARGEUR_ROUTE_KM = 6f, MIN_PX = 34f, MARGE_DU_NOMBRE_PX = 14f;
        // Le nombre d'une armée, un peu plus grand qu'un nom de ville, au sud de sa figurine.
        const float TAILLE_NOMBRE = 3.5f; const int POLICE = 64;
        static readonly NomCourbe[] AUCUN_NOM = new NomCourbe[0];
        static readonly TimeSpan DELAI = TimeSpan.FromSeconds(10); static readonly Quaternion VERS_LE_BAS = Quaternion.Euler(90, 0, 0);

        public Func<Lecture<TerresDeLaCarte>> LecteurTerres;
        public Func<Lecture<GuerresLues>> LecteurGuerres;
        public TerresDeLaCarte Terres { get; private set; }
        public string AbsenceDesTerres { get; private set; }
        public GuerresLues Guerres { get; private set; }
        public string AbsenceDesGuerres { get; private set; }
        // Change quand le pays ou le nom d'une terre change, ou quand les terres deviennent absentes : les calques recolorent alors.
        public int Version { get; private set; }
        public int CotesDeFrontiere { get; private set; }
        public string TexteLegende { get; private set; } = ENTETE;
        public bool LectureEnVol => (vol != null && !vol.IsCompleted) || (calcul != null && !calcul.IsCompleted);
        public IReadOnlyList<NomCourbe> NomsDesPays => ecriture != null ? ecriture.Noms : AUCUN_NOM;
        public NomsCourbes Ecriture => ecriture;
        public IReadOnlyList<TextMesh> NombresDesArmees => nombres;

        CarteDessinee carte; VoisinageDeCarte voisinage; List<(long, long, long, long)> lieuxQuiSeTouchent; string echecDuVoisinage;
        Task<(VoisinageDeCarte voisinage, List<(long, long, long, long)> lieux)> calcul;
        Task<(Lecture<TerresDeLaCarte> terres, Lecture<GuerresLues> guerres)> vol; double prochaine;
        string cleDesTerres; bool aRetracer; NomsCourbes ecriture; Transform racineDesArmees; Material chemin; Mesh enMarche, auSiege;
        readonly Dictionary<Color, Material> mats = new Dictionary<Color, Material>();
        readonly List<TextMesh> nombres = new List<TextMesh>();
        readonly List<UnityEngine.Object> crees = new List<UnityEngine.Object>();

        public void Installer() { carte = GetComponent<CarteDessinee>(); }
        void Update() => Pas(Time.realtimeSinceStartupAsDouble);
        void LateUpdate() => SuivreLaVue();
        void OnDestroy() { ecriture?.Dispose(); ecriture = null; foreach (var o in crees) Detruire(o); crees.Clear(); mats.Clear(); }
        // Où chaque armée se dessine à l'écran : x et y en pixels, z le rayon de sa figurine en pixels, à la taille que la
        // vue lui donne. Ce qui se cache sous une armée le lit ici.
        public void PlacesDesArmees(Camera camera, List<Vector3> places)
        {
            if (racineDesArmees == null || camera == null) return;
            foreach (Transform armee in racineDesArmees)
            {
                float kmParPixel = FormesDeCarte.KmParPixel(camera, armee.position); if (kmParPixel <= 0f) continue;
                Vector3 ecran = camera.WorldToScreenPoint(armee.position);
                places.Add(new Vector3(ecran.x, ecran.y, FormesDeCarte.RAYON_DE_L_ARMEE_KM * FormesDeCarte.EchellePourLEcran(camera, armee.position, FormesDeCarte.RAYON_DE_L_ARMEE_KM, MIN_PX) / kmParPixel));
            }
        }
        // Les noms des pays se règlent sur la vue du moment : une fois la caméra posée pour l'image.
        public void SuivreLaVue()
        {
            if (carte == null) return;
            ecriture?.Suivre(carte.camera);
            if (racineDesArmees == null || carte.camera == null) return;
            foreach (Transform armee in racineDesArmees)
            {
                float echelle = FormesDeCarte.EchellePourLEcran(carte.camera, armee.position, FormesDeCarte.RAYON_DE_L_ARMEE_KM, MIN_PX);
                armee.Find(FIGURINE).localScale = Vector3.one * echelle;
                armee.Find("Nombre").localPosition = new Vector3(0f, HAUTEUR_NOM, -(FormesDeCarte.RAYON_DE_L_ARMEE_KM * echelle + MARGE_DU_NOMBRE_PX * FormesDeCarte.KmParPixel(carte.camera, armee.position)));
            }
        }

        // Les couleurs des pays lus (`CouleursDesPays`), refaites quand les pays des terres ou leur voisinage changent ; nulles tant que les terres ne sont pas lues.
        public CouleursDesPays Couleurs { get; private set; }
        // Change quand une couleur ou un liseré de pays change : les calques repeignent alors.
        public int Coloriage { get; private set; }
        // Le pigment d'un pays et son liseré ; ceux tirés de son identifiant tant que les pays ne sont pas coloriés, le gris d'une terre sans pays pour null.
        public Color CouleurDuPays(string id) => Couleurs != null ? Couleurs.Couleur(id) : id == null ? CouleursDesPays.SansPays : CouleursDesPays.Repli(id);
        public Color LisereDuPays(string id) => Couleurs != null ? Couleurs.Lisere(id) : CalquesCarte.LisereDuPigment(CouleurDuPays(id));
        // Le pigment d'une terre : celui de son pays, le gris d'une terre sans pays ; null tant que les terres ne sont pas lues.
        public Color? CouleurDe(long cellId) => Terres == null ? (Color?)null : CouleurDuPays(Terres.PaysDe(cellId));
        // Le pays d'une maison : celui des terres dont elle tient le bourg ; une maison sans bourg est son propre pays.
        public string PaysDeLaMaison(string maison) => Terres?.Terres.FirstOrDefault(t => t.Maitre == maison)?.Pays ?? maison;
        public bool Possede(Transform t) => (ecriture != null && t.IsChildOf(ecriture.Racine)) || (racineDesArmees != null && t.IsChildOf(racineDesArmees));
        public static string Nombre(ArmeeLue armee) => TexteDuMonde.Nombre(armee.Hommes) + (armee.Hommes > 1 ? " hommes" : " homme") + (armee.Siege != null ? " · siège" : "");

        public void Pas(double t)
        {
            if (carte == null) return;
            if (calcul != null && calcul.IsCompleted)
            {
                if (calcul.IsFaulted) echecDuVoisinage = calcul.Exception.GetBaseException().Message; else { (voisinage, lieuxQuiSeTouchent) = calcul.Result; aRetracer = true; }
                calcul = null; Ecrire();
            }
            if (voisinage == null && calcul == null && echecDuVoisinage == null && carte.Lue != null && carte.Origine is PointCarte origine)
            {
                // Le voisinage des terres, et les lieux qui se touchent sur le terrain quand il est posé.
                var lue = carte.Lue; var terrain = carte.Terrain; calcul = Task.Run(() => (new VoisinageDeCarte(lue, origine), terrain != null ? CouleursDesPays.LieuxQuiSeTouchent(terrain, lue) : null));
            }
            if (vol != null && vol.IsCompleted) { var fini = vol; vol = null; Appliquer(fini); }
            if (aRetracer) Retracer();
            if (vol != null || t < prochaine || carte.PositionSurLaCarte(default, 0f) == null) return;
            prochaine = t + PERIODE_S;
            var lireTerres = LecteurTerres ?? LireTerres; var lireGuerres = LecteurGuerres ?? LireGuerres;
            vol = Task.Run(() => (SansFaute(lireTerres, "terres"), SansFaute(lireGuerres, "guerres")));
        }

        Lecture<TerresDeLaCarte> LireTerres() { using (var c = new ClientGuerre(carte.port, DELAI)) return c.LireTerres(); }
        Lecture<GuerresLues> LireGuerres() { using (var c = new ClientGuerre(carte.port, DELAI)) return c.LireGuerres(); }
        static Lecture<T> SansFaute<T>(Func<Lecture<T>> lire, string quoi) where T : class
        {
            try { return lire() ?? Lecture<T>.Absent(quoi + " : aucune lecture rendue"); }
            catch (Exception e) { return Lecture<T>.Absent(quoi + " : " + e.GetBaseException().Message); }
        }

        void Appliquer(Task<(Lecture<TerresDeLaCarte> terres, Lecture<GuerresLues> guerres)> fini)
        {
            var (terres, guerres) = fini.IsFaulted ? (Lecture<TerresDeLaCarte>.Absent("terres : " + fini.Exception.GetBaseException().Message),
                Lecture<GuerresLues>.Absent("guerres : " + fini.Exception.GetBaseException().Message)) : fini.Result;
            if (terres.Presente)
            {
                Terres = terres.Donnees; AbsenceDesTerres = null; string cle = Cle(Terres);
                if (cle != cleDesTerres) { cleDesTerres = cle; Version++; aRetracer = true; }
            }
            else
            {
                AbsenceDesTerres = terres.Absence;
                if (Terres != null) { Terres = null; cleDesTerres = null; Version++; aRetracer = true; }
            }
            if (guerres.Presente) { Guerres = guerres.Donnees; AbsenceDesGuerres = null; } else { Guerres = null; AbsenceDesGuerres = guerres.Absence; }
            DessinerLesArmees(); Ecrire();
        }

        static string Cle(TerresDeLaCarte terres)
        {
            var sb = new StringBuilder();
            foreach (var t in terres.Terres)
            {
                sb.Append(t.CellId.ToString(CultureInfo.InvariantCulture)).Append(':').Append(t.Pays);
                foreach (var lieu in t.AutresPays) sb.Append(',').Append(lieu.Rang.ToString(CultureInfo.InvariantCulture)).Append(':').Append(lieu.Pays); // un lieu qui change seul de pays change la clé
                sb.Append(';');
            }
            foreach (var p in terres.Pays) sb.Append('|').Append(p.Id).Append('=').Append(p.Nom).Append('/').Append(p.Maison?.Nom).Append('<').Append(p.Suzerain).Append('&').Append(p.Ensemble); // un lien qui change recolore
            return sb.ToString();
        }

        // Le compte des frontières et les noms, refaits seulement quand les pays des terres changent (ou quand le voisinage arrive).
        void Retracer()
        {
            aRetracer = false;
            CompterLesFrontieres(); Colorier(); NommerLesPays();
        }

        // Les couleurs des pays, d'après leurs voisinages servis ; celles d'avant restent tant qu'elles sont permises. Les armées se repeignent quand une couleur change.
        void Colorier()
        {
            CouleursDesPays neuves = Terres == null ? null : CouleursDesPays.Colorier(Terres, CouleursDesPays.VoisinsDesPays(Terres, voisinage?.Cotes, lieuxQuiSeTouchent), Couleurs);
            if (neuves == null ? Couleurs == null : neuves.MemesCouleurs(Couleurs)) { Couleurs = neuves ?? Couleurs; return; }
            Couleurs = neuves; Coloriage++; DessinerLesArmees();
        }

        // Les côtés servis qui séparent deux pays. Le terrain trace leur frontière ; il ne s'en tient ici que le compte.
        void CompterLesFrontieres()
        {
            int n = 0;
            if (voisinage != null && Terres != null)
                foreach (var cote in voisinage.Cotes) if (Terres.PaysDe(cote.Dedans) != Terres.PaysDe(cote.Dehors)) n++;
            CotesDeFrontiere = n;
        }

        // Un nom par pays, et sa maison en petit dessous, sur le plus grand morceau d'un seul tenant de ses terres : le tracé vient du terrain posé et du
        // pays servi de chaque terre, et se refait donc quand une terre change de pays.
        void NommerLesPays()
        {
            if (carte.Terrain == null || carte.Lue == null || Terres == null) { ecriture?.Ecrire(new (string, string, TraceDeNom)[0]); return; }
            if (ecriture == null) ecriture = new NomsCourbes(transform, SocleInterface.Police(titre: true), SocleInterface.Couleur("encre"), SocleInterface.Couleur("papier"), p => carte.SurLeSol(p.x, p.y, NomsCourbes.HAUTEUR));
            var rangs = new Dictionary<string, int>(); for (int k = 0; k < Terres.Pays.Count; k++) rangs[Terres.Pays[k].Id] = k;
            var pays = new int[carte.Lue.Cellules.Count];
            for (int r = 0; r < pays.Length; r++) { string id = Terres.PaysDe(carte.Lue.Cellules[r].CellId); pays[r] = id != null && rangs.TryGetValue(id, out int k) ? k : -1; }
            Dictionary<int, TraceDeNom> traces = TraceDesNoms.Tracer(carte.Terrain, pays);
            // Le nom servi du pays, et en petit dessous celui de sa maison quand il diffère.
            ecriture.Ecrire(Terres.Pays.Select((p, k) => (p.Id, p.Nom ?? "Pays sans nom", p.Maison?.Nom, traces.TryGetValue(k, out TraceDeNom trace) ? trace : null)));
            SuivreLaVue();
        }

        // Une armée par figurine, posée sur le sol à sa place : sa bannière à la couleur de son pays, un carré de piquiers quand
        // elle marche ou des tentes quand elle assiège, son nombre au sud et sa route servie, drapée sur le sol d'étape en étape.
        void DessinerLesArmees()
        {
            var garder = new HashSet<string>();
            if (Guerres != null)
                foreach (var armee in Guerres.Armees)
                {
                    if (!(carte.PositionSurLaCarte(armee.Point, HAUTEUR_ARMEE) is Vector3 ici)) continue;
                    if (racineDesArmees == null) { racineDesArmees = new GameObject(ARMEES).transform; racineDesArmees.SetParent(transform, false); crees.Add(racineDesArmees.gameObject); }
                    string nom = "Armée " + armee.Identifiant.ToString(CultureInfo.InvariantCulture); garder.Add(nom);
                    var objet = racineDesArmees.Find(nom) ?? Poser(nom);
                    objet.localPosition = ici;
                    var figurine = objet.Find(FIGURINE); figurine.GetComponent<MeshFilter>().sharedMesh = Forme(armee.Siege != null);
                    figurine.GetComponent<MeshRenderer>().sharedMaterial = Mat(CouleurDuPays(PaysDeLaMaison(armee.Maison)));
                    objet.Find("Nombre").GetComponent<TextMesh>().text = Nombre(armee);
                    var ligne = objet.Find("Route").GetComponent<LineRenderer>(); Vector3 depuis = carte.SurLeSol(ici.x, ici.z, HAUTEUR_ROUTE); var points = new List<Vector3> { depuis - ici };
                    foreach (var etape in armee.Etapes)
                        if (carte.PositionSurLaCarte(etape, HAUTEUR_ROUTE) is Vector3 p) { List<Vector3> troncon = carte.Draper(depuis, p, HAUTEUR_ROUTE); for (int k = 1; k < troncon.Count; k++) points.Add(troncon[k] - ici); depuis = p; }
                    ligne.positionCount = points.Count > 1 ? points.Count : 0; if (points.Count > 1) ligne.SetPositions(points.ToArray());
                }
            nombres.Clear();
            if (racineDesArmees == null) return;
            for (int i = racineDesArmees.childCount - 1; i >= 0; i--) { var e = racineDesArmees.GetChild(i); if (!garder.Contains(e.name)) Detruire(e.gameObject); }
            foreach (Transform e in racineDesArmees) if (garder.Contains(e.name)) nombres.Add(e.Find("Nombre").GetComponent<TextMesh>());
            SuivreLaVue();
        }

        Transform Poser(string nom)
        {
            var objet = new GameObject(nom).transform; objet.SetParent(racineDesArmees, false);
            var figurine = new GameObject(FIGURINE, typeof(MeshFilter), typeof(MeshRenderer)); figurine.transform.SetParent(objet, false);
            var rendu = figurine.GetComponent<MeshRenderer>(); rendu.shadowCastingMode = ShadowCastingMode.Off; rendu.receiveShadows = false;
            var police = SocleInterface.Police(titre: true); var texte = new GameObject("Nombre").AddComponent<TextMesh>(); texte.transform.SetParent(objet, false);
            texte.transform.SetLocalPositionAndRotation(new Vector3(0f, HAUTEUR_NOM, -FormesDeCarte.RAYON_DE_L_ARMEE_KM), VERS_LE_BAS);
            texte.font = police; texte.GetComponent<MeshRenderer>().sharedMaterial = police.material; texte.fontSize = POLICE; texte.characterSize = TAILLE_NOMBRE;
            texte.anchor = TextAnchor.MiddleCenter; texte.color = SocleInterface.Couleur("encre");
            var route = new GameObject("Route").AddComponent<LineRenderer>(); route.transform.SetParent(objet, false);
            route.useWorldSpace = false; route.widthMultiplier = LARGEUR_ROUTE_KM; route.positionCount = 0; route.shadowCastingMode = ShadowCastingMode.Off;
            if (chemin == null) { chemin = new Material(MateriauDeBase.Prendre()) { name = "Route des armées", color = SocleInterface.Couleur("cuivre") }; crees.Add(chemin); }
            route.sharedMaterial = chemin;
            return objet;
        }
        Mesh Forme(bool siege)
        {
            if (siege) { if (auSiege == null) { auSiege = FormesDeCarte.Armee(true, SocleInterface.Couleur("encre"), SocleInterface.Couleur("metal"), SocleInterface.Couleur("papier")); crees.Add(auSiege); } return auSiege; }
            if (enMarche == null) { enMarche = FormesDeCarte.Armee(false, SocleInterface.Couleur("encre"), SocleInterface.Couleur("metal"), SocleInterface.Couleur("papier")); crees.Add(enMarche); }
            return enMarche;
        }
        Material Mat(Color couleur) { if (!mats.TryGetValue(couleur, out var mat)) { mat = FormesDeCarte.Matiere(couleur); mats.Add(couleur, mat); crees.Add(mat); } return mat; }

        // Le détail de la légende : ce que montrent les traits et les disques, chaque armée nommée par son pays, et ce qui n'a pas été lu.
        void Ecrire()
        {
            var sb = new StringBuilder(ENTETE);
            if (AbsenceDesTerres != null) sb.Append("\nPays non lus : ").Append(TexteDuMonde.Absence(AbsenceDesTerres)).Append(". Couleurs des puissances du départ conservées.");
            if (echecDuVoisinage != null) sb.Append("\nFrontières non comptées : ").Append(TexteDuMonde.Absence(echecDuVoisinage));
            if (AbsenceDesGuerres != null) sb.Append("\nArmées non lues : ").Append(TexteDuMonde.Absence(AbsenceDesGuerres));
            else if (Guerres != null)
                foreach (var armee in Guerres.Armees)
                    sb.Append('\n').Append(Terres?.NomDuPays(PaysDeLaMaison(armee.Maison)) ?? "Armée d'un pays sans nom").Append(" : ").Append(Nombre(armee))
                        .Append(armee.Siege != null ? "" : armee.Destination != null ? ", en marche" : ", à l'arrêt");
            TexteLegende = sb.ToString();
        }

        static void Detruire(UnityEngine.Object o) { if (o == null) return; if (Application.isPlaying) Destroy(o); else DestroyImmediate(o); }
    }
}
