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
    // La guerre sur la carte : le pays de chaque terre (que les calques peignent), les frontières entre pays, leurs noms,
    // et les armées avec leur nombre et leur route. Tout vient de `/terres` et `/guerres`, lus hors du fil principal toutes
    // les PERIODE_S ; ici ne se fait que le dessin : aucun nombre du monde n'est calculé. Une absence se dit dans la légende.
    public sealed class CarteDeLaGuerre : MonoBehaviour
    {
        public const string FRONTIERES = "Frontières des pays", NOMS = "Noms des pays", ARMEES = "Armées de la carte";
        public const string ENTETE = "Traits rouge sombre : les frontières entre pays, chacun nommé sur sa terre. Disques : les armées, avec leurs hommes et, en cuivre, leur route.";
        public const float PERIODE_S = 2f;
        // Au-dessus des contours (0,5) et sous les flèches (0,56) ; les armées au-dessus des lieux (0,8) ; les noms des pays au-dessus des villes (1).
        public const float HAUTEUR_FRONTIERE = 0.52f, HAUTEUR_ROUTE = 0.58f, HAUTEUR_ARMEE = 0.9f, HAUTEUR_NOM = 1.1f;
        public const float LARGEUR_FRONTIERE_KM = 9f, LARGEUR_ROUTE_KM = 6f, DIAMETRE_ARMEE_KM = 18f, DIAMETRE_BORD_ARMEE_KM = 24f, EPAISSEUR_KM = 0.05f;
        // La police tirée à 64 points puis réduite : nette à l'écran. Un nom de pays près de deux fois un nom de ville, le nombre
        // d'une armée un peu plus grand qu'un nom de ville, au sud de son disque : le nom de la ville où elle se tient est au nord.
        const float TAILLE_NOM_PAYS = 7f, TAILLE_NOMBRE = 3.5f, ECART_NOMBRE_KM = -22f; const int POLICE = 64;
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
        public IReadOnlyList<TextMesh> NomsDesPays => noms;
        public IReadOnlyList<TextMesh> NombresDesArmees => nombres;

        CarteDessinee carte; VoisinageDeCarte voisinage; string echecDuVoisinage; Task<VoisinageDeCarte> calcul;
        Task<(Lecture<TerresDeLaCarte> terres, Lecture<GuerresLues> guerres)> vol; double prochaine;
        string cleDesTerres; bool aRetracer; Transform frontieres, racineDesNoms, racineDesArmees; Mesh maillage; Material trait, chemin, bord;
        readonly Dictionary<Color, Material> mats = new Dictionary<Color, Material>();
        readonly List<TextMesh> noms = new List<TextMesh>(), nombres = new List<TextMesh>();
        readonly List<UnityEngine.Object> crees = new List<UnityEngine.Object>();

        public void Installer() { carte = GetComponent<CarteDessinee>(); }
        void Update() => Pas(Time.realtimeSinceStartupAsDouble);
        void OnDestroy() { foreach (var o in crees) Detruire(o); crees.Clear(); mats.Clear(); }

        // La teinte d'un pays ne dépend que de son identifiant, comme celle d'une puissance de 1400.
        public static Color CouleurDuPays(string id)
        {
            if (string.IsNullOrEmpty(id)) return MaillageDeCarte.CouleurSansPuissance;
            uint h = 2166136261u; foreach (char c in id) { h ^= c; h *= 16777619u; }
            return MaillageDeCarte.CouleurPourPuissance(h);
        }
        // La teinte servie d'une terre : celle de son pays, le gris d'une terre sans pays ; null tant que les terres ne sont pas lues.
        public Color? CouleurDe(long cellId) => Terres == null ? (Color?)null : CouleurDuPays(Terres.PaysDe(cellId));
        // Le pays d'une maison : celui des terres dont elle tient le bourg ; une maison sans bourg est son propre pays.
        public string PaysDeLaMaison(string maison) => Terres?.Terres.FirstOrDefault(t => t.Maitre == maison)?.Pays ?? maison;
        public bool Possede(Transform t) => (racineDesNoms != null && t.IsChildOf(racineDesNoms)) || (racineDesArmees != null && t.IsChildOf(racineDesArmees));
        public static string Nombre(ArmeeLue armee) => TexteDuMonde.Nombre(armee.Hommes) + (armee.Hommes > 1 ? " hommes" : " homme") + (armee.Siege != null ? " · siège" : "");

        public void Pas(double t)
        {
            if (carte == null) return;
            if (calcul != null && calcul.IsCompleted)
            {
                if (calcul.IsFaulted) echecDuVoisinage = calcul.Exception.GetBaseException().Message; else { voisinage = calcul.Result; aRetracer = true; }
                calcul = null; Ecrire();
            }
            if (voisinage == null && calcul == null && echecDuVoisinage == null && carte.Lue != null && carte.Origine is PointCarte origine)
            {
                var lue = carte.Lue; calcul = Task.Run(() => new VoisinageDeCarte(lue, origine));
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
            foreach (var t in terres.Terres) sb.Append(t.CellId.ToString(CultureInfo.InvariantCulture)).Append(':').Append(t.Pays).Append(';');
            foreach (var p in terres.Pays) sb.Append('|').Append(p.Id).Append('=').Append(p.Nom);
            return sb.ToString();
        }

        // Les frontières et les noms, refaits seulement quand les pays des terres changent (ou quand le voisinage arrive).
        void Retracer()
        {
            aRetracer = false;
            TracerLesFrontieres(); NommerLesPays();
        }

        void TracerLesFrontieres()
        {
            var sommets = new List<Vector3>(); var normales = new List<Vector3>(); var triangles = new List<int>(); int n = 0;
            if (voisinage != null && Terres != null)
                foreach (var cote in voisinage.Cotes)
                {
                    if (Terres.PaysDe(cote.Dedans) == Terres.PaysDe(cote.Dehors)) continue;
                    Vector3 a = new Vector3(cote.De.x, HAUTEUR_FRONTIERE, cote.De.y), b = new Vector3(cote.A.x, HAUTEUR_FRONTIERE, cote.A.y), d = (b - a).normalized;
                    Vector3 p = new Vector3(d.z, 0f, -d.x) * (LARGEUR_FRONTIERE_KM / 2f); int i = sommets.Count;
                    sommets.Add(a - p); sommets.Add(b - p); sommets.Add(b + p); sommets.Add(a + p);
                    normales.AddRange(new[] { Vector3.up, Vector3.up, Vector3.up, Vector3.up });
                    // Une seule face, tournée vers le haut et éclairée comme les terres : (a − p, b − p, b + p) tourne dans le sens
                    // horaire vu d'en haut, la règle des triangles des terres (`TriangulationDeCarte.Ajouter`).
                    triangles.AddRange(new[] { i, i + 1, i + 2, i, i + 2, i + 3 });
                    n++;
                }
            CotesDeFrontiere = n;
            if (frontieres == null)
            {
                var objet = new GameObject(FRONTIERES, typeof(MeshFilter), typeof(MeshRenderer)); objet.transform.SetParent(transform, false); crees.Add(objet);
                frontieres = objet.transform; maillage = new Mesh { name = FRONTIERES, indexFormat = IndexFormat.UInt32 }; crees.Add(maillage);
                objet.GetComponent<MeshFilter>().sharedMesh = maillage;
                trait = new Material(MateriauDeBase.Prendre()) { name = FRONTIERES, color = SocleInterface.Couleur("sang") }; crees.Add(trait);
                var rendu = objet.GetComponent<MeshRenderer>(); rendu.sharedMaterial = trait; rendu.shadowCastingMode = ShadowCastingMode.Off;
            }
            maillage.Clear(); maillage.SetVertices(sommets); maillage.SetNormals(normales); maillage.SetTriangles(triangles, 0); maillage.RecalculateBounds();
        }

        // Un nom par pays, au centre de celle de ses terres qui est la plus proche du centre de toutes ses terres.
        void NommerLesPays()
        {
            foreach (var nom in noms) if (nom != null) Detruire(nom.gameObject);
            noms.Clear();
            if (voisinage == null || Terres == null) return;
            if (racineDesNoms == null) { racineDesNoms = new GameObject(NOMS).transform; racineDesNoms.SetParent(transform, false); crees.Add(racineDesNoms.gameObject); }
            var police = SocleInterface.Police(titre: true);
            foreach (var pays in Terres.Pays)
            {
                var centres = Terres.Terres.Where(t => t.Pays == pays.Id && voisinage.Centres.ContainsKey(t.CellId)).Select(t => voisinage.Centres[t.CellId]).ToList();
                if (centres.Count == 0) continue;
                Vector2 moyen = centres.Aggregate(Vector2.zero, (s, c) => s + c) / centres.Count, retenu = centres[0];
                foreach (var c in centres) if ((c - moyen).sqrMagnitude < (retenu - moyen).sqrMagnitude) retenu = c;
                var texte = new GameObject("Pays " + pays.Id).AddComponent<TextMesh>(); texte.transform.SetParent(racineDesNoms, false);
                texte.transform.SetLocalPositionAndRotation(new Vector3(retenu.x, HAUTEUR_NOM, retenu.y), VERS_LE_BAS);
                texte.font = police; texte.GetComponent<MeshRenderer>().sharedMaterial = police.material; texte.fontSize = POLICE; texte.characterSize = TAILLE_NOM_PAYS;
                texte.anchor = TextAnchor.MiddleCenter; texte.color = SocleInterface.Couleur("encre"); texte.text = pays.Nom ?? "Pays sans nom";
                noms.Add(texte);
            }
        }

        // Une armée par repère : un disque à sa place, à la couleur de son pays, son nombre au sud et sa route servie.
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
                    objet.Find("Disque").GetComponent<MeshRenderer>().sharedMaterial = Mat(CouleurDuPays(PaysDeLaMaison(armee.Maison)));
                    objet.Find("Nombre").GetComponent<TextMesh>().text = Nombre(armee);
                    var ligne = objet.Find("Route").GetComponent<LineRenderer>(); var points = new List<Vector3> { new Vector3(0f, HAUTEUR_ROUTE - HAUTEUR_ARMEE, 0f) };
                    foreach (var etape in armee.Etapes) if (carte.PositionSurLaCarte(etape, HAUTEUR_ROUTE) is Vector3 p) points.Add(p - new Vector3(ici.x, HAUTEUR_ARMEE, ici.z));
                    ligne.positionCount = points.Count > 1 ? points.Count : 0; if (points.Count > 1) ligne.SetPositions(points.ToArray());
                }
            nombres.Clear();
            if (racineDesArmees == null) return;
            for (int i = racineDesArmees.childCount - 1; i >= 0; i--) { var e = racineDesArmees.GetChild(i); if (!garder.Contains(e.name)) Detruire(e.gameObject); }
            foreach (Transform e in racineDesArmees) if (garder.Contains(e.name)) nombres.Add(e.Find("Nombre").GetComponent<TextMesh>());
        }

        Transform Poser(string nom)
        {
            var objet = new GameObject(nom).transform; objet.SetParent(racineDesArmees, false);
            Disque(objet, "Bord", Bord(), DIAMETRE_BORD_ARMEE_KM, -0.12f); Disque(objet, "Disque", Mat(Color.white), DIAMETRE_ARMEE_KM, 0f);
            var police = SocleInterface.Police(titre: true); var texte = new GameObject("Nombre").AddComponent<TextMesh>(); texte.transform.SetParent(objet, false);
            texte.transform.SetLocalPositionAndRotation(new Vector3(0f, HAUTEUR_NOM - HAUTEUR_ARMEE, ECART_NOMBRE_KM), VERS_LE_BAS);
            texte.font = police; texte.GetComponent<MeshRenderer>().sharedMaterial = police.material; texte.fontSize = POLICE; texte.characterSize = TAILLE_NOMBRE;
            texte.anchor = TextAnchor.MiddleCenter; texte.color = SocleInterface.Couleur("encre");
            var route = new GameObject("Route").AddComponent<LineRenderer>(); route.transform.SetParent(objet, false);
            route.useWorldSpace = false; route.widthMultiplier = LARGEUR_ROUTE_KM; route.positionCount = 0; route.shadowCastingMode = ShadowCastingMode.Off;
            if (chemin == null) { chemin = new Material(MateriauDeBase.Prendre()) { name = "Route des armées", color = SocleInterface.Couleur("cuivre") }; crees.Add(chemin); }
            route.sharedMaterial = chemin;
            return objet;
        }
        void Disque(Transform parent, string nom, Material mat, float diametre, float haut)
        {
            var o = GameObject.CreatePrimitive(PrimitiveType.Cylinder); o.name = nom; Detruire(o.GetComponent<Collider>()); o.GetComponent<MeshRenderer>().sharedMaterial = mat;
            o.transform.SetParent(parent, false); o.transform.localPosition = new Vector3(0f, haut, 0f); o.transform.localScale = new Vector3(diametre, EPAISSEUR_KM, diametre);
        }
        Material Mat(Color couleur) { if (!mats.TryGetValue(couleur, out var mat)) { mat = new Material(MateriauDeBase.Prendre()) { color = couleur }; mats.Add(couleur, mat); crees.Add(mat); } return mat; }
        Material Bord() { if (bord == null) { bord = new Material(MateriauDeBase.Prendre()) { color = SocleInterface.Couleur("encre") }; crees.Add(bord); } return bord; }

        // Le détail de la légende : ce que montrent les traits et les disques, chaque armée nommée par son pays, et ce qui n'a pas été lu.
        void Ecrire()
        {
            var sb = new StringBuilder(ENTETE);
            if (AbsenceDesTerres != null) sb.Append("\nPays non lus : ").Append(TexteDuMonde.Absence(AbsenceDesTerres)).Append(". Couleurs des puissances du départ conservées.");
            if (echecDuVoisinage != null) sb.Append("\nFrontières non tracées : ").Append(TexteDuMonde.Absence(echecDuVoisinage));
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
