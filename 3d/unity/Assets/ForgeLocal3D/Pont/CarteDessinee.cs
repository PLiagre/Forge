using System.Collections.Generic;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.UI;

namespace Forge.Pont {
    // La carte de 1400 servie par `sim/` : un terrain en relief d'un seul tenant, où chaque cellule servie a sa teinte,
    // au départ celle de sa puissance, sans aucun nombre du monde calculé ici. Lecture et levé du terrain partent hors
    // du fil principal ; la pose se fait dans Update, une seule fois. Sans carte, le texte dit pourquoi et rien n'est
    // posé ; la lecture repart plus tard. Une vue change la teinte d'une cellule par `Teinter`, jamais par un objet.
    // Les traits sont dessinés par le terrain lui-même, aux côtés servis : le bord de chaque cellule, la côte et ses
    // lignes d'eau, et la frontière entre deux cellules que `Rattacher` donne à des pays différents, doublée d'un
    // liseré à la couleur de chaque pays. Au départ, chaque cellule est rattachée à sa puissance servie.
    // Le terrain se dessine en relief : la mer est au niveau 0 de la carte, et les hauteurs du terrain levé y sont
    // réduites de `ECHELLE_DU_RELIEF`, pour qu'une montagne se voie sous une caméra inclinée sans cacher ce qui est
    // derrière elle. Tout ce qui se pose sur la carte se pose sur ce sol : `PositionSurLaCarte` rend un point à sa
    // hauteur au-dessus de lui, `Draper` une ligne qui le suit, `SolSous` le point du sol sous un point de l'écran.
    // Le nom de chaque ville, et sans caméra donnée, une à soi qui tient toute la carte.
    // Cette caméra montre la `Vue`, en perspective, que le joueur glisse et zoome (`ParcoursDeCarte`) sans sortir de la carte.
    public sealed class CarteDessinee : MonoBehaviour {
        public const string MESSAGE_ABSENCE = "le monde ne répond pas";
        public const float PERIODE_RELECTURE_S = 2f;
        public const float HAUTEUR_NOM = 1f;
        // Ce que le dessin garde des hauteurs du terrain levé ; et le pas, en km, d'une ligne drapée ou d'un rayon qui cherche le sol.
        public const float ECHELLE_DU_RELIEF = 0.3f, PAS_DU_DRAPE_KM = 6f, PAS_DU_RAYON_KM = 0.5f;
        private const int PAS_MAX_DU_RAYON = 256, AFFINAGES = 12;
        public const string TERRAIN = "Terrain de la carte", SHADER_DU_TERRAIN = "Forge/CarteRelief";
        private const string SANS_SHADER = "carte non dessinée : shader " + SHADER_DU_TERRAIN + " absent";
        private const int LARGEUR_PALETTE = 256; // une teinte par cellule, rangée par lignes ; la case 0 est la mer
        private const string PUISSANCE = "puissance "; // la clé du pays de départ d'une cellule : sa puissance servie
        private const float ECART_PLAN = 0.2f; private const int TAILLE_POLICE = 24;
        private const int TAILLE_NOM = 16; private const float TAILLE_CARACTERE = 25f; // une ligne de nom : environ 40 km, dessinée près de sa taille à l'écran
        private static readonly Color MER = new Color(0.08f, 0.16f, 0.3f), RIVAGE = new Color(0.2f, 0.3f, 0.42f), ROCHE = new Color(0.85f, 0.83f, 0.78f), BORD = new Color(0.1f, 0.08f, 0.06f), EAUX = new Color(0.5f, 0.6f, 0.7f);
        private static readonly Quaternion VERS_LE_BAS = Quaternion.Euler(90, 0, 0);
        public int port = PanneauLieu.DEFAULT_SERVICE_PORT;
        public new Camera camera;
        private Text texte; private Canvas toile; private ClientCarte client;
        private Task<(CarteLue lue, TerrainDeCarte terrain, string absence)> enCours;
        private double prochaineLecture; private bool close; // carte posée, ou refusée faute de matériau : plus aucune lecture ne part
        private bool cameraCreee; private Bounds boite; // la boîte des cellules, en local : ce que la caméra créée cadre
        private readonly List<Object> crees = new List<Object>();
        private Material matiere; private Texture2D palette; private Color[] teintes; private bool aVerser; // la palette, et si elle attend d'être versée au shader
        private Dictionary<long, int> rangs; private bool[] posees; private int nombrePosees; // le rang servi de chaque cellule, et celles que le terrain dessine
        private Color mer = MER, rivage = RIVAGE, roche = ROCHE, encreDesCotes = BORD, encreDesBords = BORD, encreDesFrontieres = BORD, encreDesEaux = EAUX;
        // Les pays : la clé de chacun par indice (0 : aucun pays), l'indice du pays de chaque case de la palette, et la
        // couleur du liseré de chaque pays. Les deux tables attendent d'être versées quand un rattachement les change.
        private List<string> cles; private Dictionary<string, int> indicesDesPays; private ushort[] indices; private Color[] couleursDesPays;
        private Texture2D paysDesCellules, teintesDesPays; private bool paysAVerser;
        // Les distances aux frontières, un octet par texel ; la zone à mesurer de nouveau, et si la grille attend d'être versée.
        private Texture2D frontieres; private byte[] champ; private RectInt? sale; private bool frontieresAVerser;
        private long? marquee; private Color marque; // la cellule marquée et la couleur qui couvre sa teinte
        private readonly Dictionary<long, Color> eclats = new Dictionary<long, Color>(); // les cellules éclairées et la couleur qui couvre leur teinte

        public string TexteAffiche => texte != null ? texte.text : null;
        public int CellulesServies { get; private set; } = -1;
        // Les cellules servies que le terrain dessine : celles qui ont au moins un texel et une teinte, et qu'on n'a pas retirées.
        public int CellulesPosees => nombrePosees;
        // Le terrain levé de la carte posée ; null avant la pose.
        public TerrainDeCarte Terrain { get; private set; }
        public bool LectureEnVol => enCours != null && !enCours.IsCompleted;
        public VueDeCarte Vue { get; private set; } // ce que la caméra créée montre ; null sans carte posée ou avec une caméra donnée
        private ReperageDeCarte reperage; // la cellule sous un point
        private PointCarte? origine; // l'origine de Mailler, gardée à la pose
        // La carte servie posée, et l'origine de ses km locaux : ce que les vues tirent des contours. Nulles avant la pose.
        public CarteLue Lue { get; private set; }
        public PointCarte? Origine => origine;
        // Un point servi (EPSG:3035, en m), en local dans la carte, à cette hauteur au-dessus du sol (en mer, au-dessus
        // de l'eau) ; null tant que la carte n'est pas posée.
        public Vector3? PositionSurLaCarte(PointCarte point, float hauteur) {
            if (!origine.HasValue) return null;
            Vector3 p = Place(point, origine.Value, 0f); p.y = Mathf.Max(HauteurDuSol(p.x, p.z), 0f) + hauteur; return p;
        }
        // La hauteur du sol dessiné sous un point en km locaux : 0 au niveau de la mer, négative sur les fonds ; 0 sans carte posée.
        public float HauteurDuSol(float x, float z) => Terrain != null ? (Terrain.SolDuMaillage(x, z) + TerrainDeCarte.PLAFOND) * ECHELLE_DU_RELIEF : 0f;
        // Le même point en local, posé à cette hauteur au-dessus du sol (en mer, au-dessus de l'eau).
        public Vector3 SurLeSol(float x, float z, float hauteur) => new Vector3(x, Mathf.Max(HauteurDuSol(x, z), 0f) + hauteur, z);
        // La ligne de `a` à `b` (en local), drapée sur le sol à cette hauteur : un point tous les `PAS_DU_DRAPE_KM` au plus, bouts compris.
        public List<Vector3> Draper(Vector3 a, Vector3 b, float hauteur) {
            float longueur = new Vector2(b.x - a.x, b.z - a.z).magnitude; int pas = Mathf.Max(1, Mathf.CeilToInt(longueur / PAS_DU_DRAPE_KM));
            var points = new List<Vector3>(pas + 1);
            for (int k = 0; k <= pas; k++) points.Add(SurLeSol(Mathf.Lerp(a.x, b.x, k / (float)pas), Mathf.Lerp(a.z, b.z, k / (float)pas), hauteur));
            return points;
        }
        // Le point du sol que touche un rayon du monde, en coordonnées du monde : le rayon descend du plus haut du
        // relief par pas de `PAS_DU_RAYON_KM`, et le point où il passe sous le sol s'affine par moitiés. Null sans carte
        // posée, ou si le rayon ne descend pas vers la carte.
        public Vector3? SolSur(Ray rayon) {
            if (Terrain == null) return null;
            Vector3 o = transform.InverseTransformPoint(rayon.origin), d = transform.InverseTransformDirection(rayon.direction);
            float haut = TerrainDeCarte.PLAFOND * ECHELLE_DU_RELIEF, bas = -TerrainDeCarte.FOND * ECHELLE_DU_RELIEF;
            if (d.y >= -1e-6f || o.y <= bas) return null;
            float t0 = Mathf.Max(0f, (haut - o.y) / d.y), t1 = (bas - o.y) / d.y;
            float Ecart(float t) { Vector3 p = o + d * t; return p.y - HauteurDuSol(p.x, p.z); }
            float horizontal = new Vector2(d.x, d.z).magnitude * (t1 - t0); int pas = Mathf.Clamp(Mathf.CeilToInt(horizontal / PAS_DU_RAYON_KM), 1, PAS_MAX_DU_RAYON);
            float dessus = t0, dessous = t1;
            for (int k = 1; k <= pas; k++) { float t = Mathf.Lerp(t0, t1, k / (float)pas); if (Ecart(t) <= 0f) { dessous = t; break; } dessus = t; }
            for (int k = 0; k < AFFINAGES; k++) { float milieu = (dessus + dessous) / 2f; if (Ecart(milieu) <= 0f) dessous = milieu; else dessus = milieu; }
            return transform.TransformPoint(o + d * ((dessus + dessous) / 2f));
        }
        // Le point du sol sous un point de l'écran, par la caméra de la carte ; null sans caméra, sans carte posée, ou hors du sol.
        public Vector3? SolSous(Vector2 ecran) => camera != null ? SolSur(camera.ScreenPointToRay(ecran)) : null;
        // La cellule servie sous un point du monde (à la verticale de la carte) ; null dans la mer ou sans carte posée.
        public CelluleDeCarte CelluleSous(Vector3 monde) {
            if (reperage == null) return null;
            Vector3 local = transform.InverseTransformPoint(monde); return reperage.Sous(local.x, local.z);
        }
        // La teinte dont une cellule posée est dessinée ; null si le terrain ne la dessine pas.
        public Color? TeinteDe(long cellId) => rangs != null && rangs.TryGetValue(cellId, out int rang) && posees[rang] ? teintes[rang + 1] : (Color?)null;
        // Dessine une cellule posée d'une autre teinte ; faux si le terrain ne la dessine pas.
        public bool Teinter(long cellId, Color teinte) {
            if (rangs == null || !rangs.TryGetValue(cellId, out int rang) || !posees[rang]) return false;
            teinte.a = 1f; teintes[rang + 1] = teinte; aVerser = true; return true;
        }
        // Retire une cellule du dessin : son sol rend la mer, elle perd sa marque et ne compte plus parmi les posées.
        public bool Retirer(long cellId) {
            if (rangs == null || !rangs.TryGetValue(cellId, out int rang) || !posees[rang]) return false;
            posees[rang] = false; nombrePosees--; teintes[rang + 1] = Color.clear; if (marquee == cellId) marquee = null; eclats.Remove(cellId); aVerser = true;
            Salir(Terrain.ZoneDe(rang)); return true; // ses voisines n'ont plus de frontière avec elle
        }
        // Rattache une cellule posée à un pays, nommé par sa clé, et donne au pays la couleur de son liseré ; sans clé,
        // la cellule n'est à aucun pays. Une frontière sépare deux cellules voisines qui ne sont pas au même pays.
        // Faux si le terrain ne la dessine pas.
        public bool Rattacher(long cellId, string pays, Color couleur) {
            if (rangs == null || !rangs.TryGetValue(cellId, out int rang) || !posees[rang]) return false;
            int indice = 0;
            if (!string.IsNullOrEmpty(pays) && !indicesDesPays.TryGetValue(pays, out indice)) {
                if (cles.Count == couleursDesPays.Length) { indices[rang + 1] = 0; Tasser(); Salir(Terrain.ZoneDe(rang)); }
                indice = cles.Count; cles.Add(pays); indicesDesPays[pays] = indice;
            }
            couleur.a = 1f;
            if (indice > 0 && couleursDesPays[indice] != couleur) { couleursDesPays[indice] = couleur; paysAVerser = true; }
            if (indices[rang + 1] != indice) { indices[rang + 1] = (ushort)indice; paysAVerser = true; Salir(Terrain.ZoneDe(rang)); }
            return true;
        }
        // La clé du pays d'une cellule posée ; null si elle n'est à aucun pays ou que le terrain ne la dessine pas.
        public string PaysDe(long cellId) => rangs != null && rangs.TryGetValue(cellId, out int rang) && posees[rang] ? cles[indices[rang + 1]] : null;
        // Sous un point en km locaux, la distance en km à la plus proche frontière du pays qui tient ce point, telle
        // que le terrain la dessine ; la portée des frontières quand elle est plus loin, en mer ou sans frontière ;
        // -1 sans carte posée.
        public float DistanceALaFrontiere(float x, float z) {
            if (champ == null) return -1f;
            Mesurer(); return Terrain.FrontiereEn(champ, x, z);
        }
        // Les encres des traits du terrain : la côte, le bord des cellules, les frontières, les lignes d'eau.
        public void Encrer(Color cotes, Color bords, Color desFrontieres, Color eaux) {
            encreDesCotes = cotes; encreDesBords = bords; encreDesFrontieres = desFrontieres; encreDesEaux = eaux;
            if (matiere == null) return;
            matiere.SetColor("_EncreDesCotes", cotes); matiere.SetColor("_EncreDesBords", bords); matiere.SetColor("_EncreDesFrontieres", desFrontieres); matiere.SetColor("_EncreDesEaux", eaux);
        }
        // La cellule marquée, ou null : une seule à la fois.
        public long? Marquee => marquee;
        // Couvre une cellule posée d'une couleur sans toucher à sa teinte, qui revient quand la marque part ; faux si le
        // terrain ne la dessine pas, et la marque d'avant reste.
        public bool Marquer(long cellId, Color couleur) {
            if (rangs == null || !rangs.TryGetValue(cellId, out int rang) || !posees[rang]) return false;
            couleur.a = 1f; marquee = cellId; marque = couleur; aVerser = true; return true;
        }
        public void Demarquer() { if (marquee.HasValue) { marquee = null; aVerser = true; } }
        // Éclaire une cellule posée : comme la marque, la couleur couvre sa teinte sans y toucher, et le relief, les
        // bords et les frontières s'y dessinent toujours. Autant de cellules qu'on veut ; la marque passe devant.
        // Faux si le terrain ne la dessine pas.
        public bool Eclairer(long cellId, Color couleur) {
            if (rangs == null || !rangs.TryGetValue(cellId, out int rang) || !posees[rang]) return false;
            couleur.a = 1f; if (!eclats.TryGetValue(cellId, out Color deja) || deja != couleur) { eclats[cellId] = couleur; aVerser = true; }
            return true;
        }
        public void Eteindre(long cellId) { if (eclats.Remove(cellId)) aVerser = true; }
        // La couleur dont une cellule est éclairée ; null si elle ne l'est pas.
        public Color? EclatDe(long cellId) => eclats.TryGetValue(cellId, out Color couleur) ? couleur : (Color?)null;
        // Les couleurs de l'habillage : la mer au large (celle du fond de la caméra), la mer au rivage, les cimes.
        public void Habiller(Color large, Color auRivage, Color cimes) {
            mer = large; rivage = auRivage; roche = cimes;
            if (matiere == null) return;
            matiere.SetColor("_Mer", mer); matiere.SetColor("_Rivage", rivage); matiere.SetColor("_Roche", roche);
        }
        // Pose une carte déjà lue, sans service : le terrain se lève sur place. Sans effet sur une carte déjà posée.
        public void Montrer(CarteLue lue) { if (!close) Poser(lue, TerrainDeCarte.Lever(lue)); }
        private void Start() => Demarrer();
        private void LateUpdate() => Verser();
        private void Update() => Pas(Time.realtimeSinceStartupAsDouble);
        private void OnDestroy() => Arreter();
        // Sur la caméra posée, comme PanneauLieu, juste derrière son plan proche : la capture voit le texte.
        public void Demarrer() {
            if (camera == null) { // la sienne, vue de la mer, cadrée une fois la carte posée
                camera = new GameObject("Caméra de la carte").AddComponent<Camera>(); camera.transform.SetParent(transform, false); cameraCreee = true;
                camera.orthographic = false; camera.fieldOfView = VueDeCarte.CHAMP; camera.clearFlags = CameraClearFlags.SolidColor; camera.backgroundColor = MER;
            }
            toile = new GameObject("Toile de la carte", typeof(RectTransform)).AddComponent<Canvas>();
            toile.transform.SetParent(transform, false);
            toile.renderMode = camera != null ? RenderMode.ScreenSpaceCamera : RenderMode.ScreenSpaceOverlay; toile.worldCamera = camera;
            if (camera != null) toile.planeDistance = camera.nearClipPlane + ECART_PLAN;
            texte = new GameObject("Texte", typeof(RectTransform)).AddComponent<Text>();
            texte.transform.SetParent(toile.transform, false);
            var cadre = (RectTransform)texte.transform; cadre.anchorMin = Vector2.zero; cadre.anchorMax = Vector2.one;
            texte.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf"); texte.fontSize = TAILLE_POLICE; texte.color = Color.white;
            Dire("carte : en attente de 127.0.0.1:" + port);
            client = new ClientCarte(port, ClientCarte.DelaiMinimal);
        }
        public void Arreter() {
            client?.Dispose(); client = null; enCours = null;
            foreach (Object o in crees) if (Application.isPlaying) Destroy(o); else DestroyImmediate(o);
            crees.Clear();
        }
        public void Pas(double maintenant) {
            if (client == null) return;
            if (enCours != null && enCours.IsCompleted) {
                var lu = enCours.Result; enCours = null;
                if (lu.absence == null) Poser(lu.lue, lu.terrain);
                else { Dire(MESSAGE_ABSENCE + "\n" + lu.absence); prochaineLecture = maintenant + PERIODE_RELECTURE_S; }
            }
            Cadrer(); // la fenêtre peut avoir changé de forme
            Verser();
            if (close || enCours != null || maintenant < prochaineLecture) return;
            ClientCarte lecteur = client; enCours = Task.Run(() => Lire(lecteur));
        }
        // Hors du fil principal : la carte servie, puis son terrain ; une carte que le levé refuse est une absence.
        private static (CarteLue, TerrainDeCarte, string) Lire(ClientCarte lecteur) {
            LectureCarte lecture = lecteur.Lire();
            if (!lecture.Presente) return (null, null, lecture.Absence);
            try { return (lecture.Carte, TerrainDeCarte.Lever(lecture.Carte), null); }
            catch (System.ArgumentException erreur) { return (null, null, "carte : " + erreur.Message); }
        }
        private void Poser(CarteLue lue, TerrainDeCarte terrain) {
            close = true;
            Shader relief = Resources.Load<Shader>(SHADER_DU_TERRAIN);
            if (relief == null) { Dire(SANS_SHADER); return; }
            var maillage = new Mesh { name = TERRAIN, indexFormat = IndexFormat.UInt32 };
            maillage.SetVertices(terrain.SommetsDuMaillage); maillage.SetUVs(0, terrain.UvDuMaillage); maillage.SetTriangles(terrain.TrianglesDuMaillage, 0);
            maillage.RecalculateBounds(); crees.Add(maillage);
            // Les numéros de cellules et les distances se lisent au texel près ; le relief se lit entre ses altitudes.
            Texture2D cellules = Creer("Cellules de la carte", terrain.Largeur, terrain.Hauteur, TextureFormat.R16, FilterMode.Point, true);
            cellules.SetPixelData(terrain.TexelsDesCellules, 0); cellules.Apply(false, true);
            Texture2D altitudes = Creer("Relief de la carte", terrain.LargeurDuRelief, terrain.HauteurDuRelief, TextureFormat.RFloat, FilterMode.Bilinear, true);
            altitudes.SetPixelData(terrain.TexelsDuRelief, 0); altitudes.Apply(false, true);
            Texture2D bords = Creer("Bords de la carte", terrain.Largeur, terrain.Hauteur, TextureFormat.RG16, FilterMode.Point, true);
            bords.SetPixelData(terrain.TexelsDesBords, 0); bords.Apply(false, true);
            frontieres = Creer("Frontières de la carte", terrain.Largeur, terrain.Hauteur, TextureFormat.R8, FilterMode.Point, true);
            champ = new byte[terrain.Largeur * terrain.Hauteur]; Terrain = terrain; sale = terrain.Tout;
            int servies = lue.Cellules.Count;
            palette = Creer("Teintes de la carte", LARGEUR_PALETTE, (servies + LARGEUR_PALETTE) / LARGEUR_PALETTE, TextureFormat.RGBA32, FilterMode.Point, false);
            teintes = new Color[palette.width * palette.height]; rangs = new Dictionary<long, int>(servies); posees = new bool[servies]; nombrePosees = 0;
            // Les deux tables des pays se rangent comme la palette : la case d'une cellule dit son pays, celle d'un pays sa couleur.
            paysDesCellules = Creer("Pays des cellules", palette.width, palette.height, TextureFormat.R16, FilterMode.Point, true);
            teintesDesPays = Creer("Teintes des pays", palette.width, palette.height, TextureFormat.RGBA32, FilterMode.Point, false);
            indices = new ushort[teintes.Length]; couleursDesPays = new Color[teintes.Length]; cles = new List<string> { null }; indicesDesPays = new Dictionary<string, int>();
            for (int rang = 0; rang < servies; rang++) {
                CelluleDeCarte cellule = lue.Cellules[rang]; rangs[cellule.CellId] = rang;
                if (terrain.TexelsDe(rang) == 0) continue; // sans texel, rien ne la dessine
                Color teinte = MaillageDeCarte.CouleurDe(cellule); teinte.a = 1f; teintes[rang + 1] = teinte; posees[rang] = true; nombrePosees++;
                if (cellule.Puissance != null) Rattacher(cellule.CellId, PUISSANCE + cellule.Puissance.Id, teinte);
            }
            matiere = new Material(relief) { name = TERRAIN }; crees.Add(matiere);
            matiere.SetTexture("_Cellules", cellules); matiere.SetTexture("_Relief", altitudes); matiere.SetTexture("_Palette", palette);
            matiere.SetTexture("_Bords", bords); matiere.SetTexture("_Frontieres", frontieres); matiere.SetTexture("_Pays", paysDesCellules); matiere.SetTexture("_TeintesDesPays", teintesDesPays);
            matiere.SetFloat("_PasDuRelief", terrain.PasDuRelief); matiere.SetFloat("_Fond", TerrainDeCarte.FOND); matiere.SetFloat("_Plafond", TerrainDeCarte.PLAFOND);
            matiere.SetFloat("_Pas", terrain.Pas); matiere.SetFloat("_PorteeDesBords", TerrainDeCarte.PORTEE_DES_BORDS_KM); matiere.SetFloat("_PorteeDesFrontieres", TerrainDeCarte.PORTEE_DES_FRONTIERES_KM);
            Habiller(mer, rivage, roche); Encrer(encreDesCotes, encreDesBords, encreDesFrontieres, encreDesEaux); aVerser = true; paysAVerser = true; Verser();
            // Le maillage levé a sa plus haute cime au plan 0 : il se pose de façon que la mer soit au niveau 0 de la carte, ses hauteurs réduites.
            var sol = new GameObject(TERRAIN, typeof(MeshFilter), typeof(MeshRenderer)); sol.transform.SetParent(transform, false);
            sol.transform.localPosition = new Vector3(0f, TerrainDeCarte.PLAFOND * ECHELLE_DU_RELIEF, 0f); sol.transform.localScale = new Vector3(1f, ECHELLE_DU_RELIEF, 1f);
            sol.GetComponent<MeshFilter>().sharedMesh = maillage;
            var rendu = sol.GetComponent<MeshRenderer>(); rendu.sharedMaterial = matiere; rendu.shadowCastingMode = ShadowCastingMode.Off; rendu.receiveShadows = false;
            boite = terrain.Boite;
            origine = terrain.Origine; Nommer(lue, terrain.Origine); reperage = new ReperageDeCarte(lue, terrain.Origine); Lue = lue;
            if (cameraCreee && camera != null && nombrePosees > 0) Vue = new VueDeCarte(boite, camera.aspect); // toute la carte
            CellulesServies = servies; Dire(""); Cadrer();
        }
        private Texture2D Creer(string nom, int largeur, int hauteur, TextureFormat format, FilterMode filtre, bool lineaire) {
            var texture = new Texture2D(largeur, hauteur, format, false, lineaire) { name = nom, filterMode = filtre, wrapMode = TextureWrapMode.Clamp };
            crees.Add(texture); return texture;
        }
        // Rien ne part au shader qui n'ait changé depuis le dernier versement : la palette pour une teinte ou la marque,
        // la grille des frontières et les tables des pays pour un rattachement ou un retrait.
        private void Verser() {
            if (palette == null) return;
            if (aVerser) {
                aVerser = false; palette.SetPixels(teintes);
                foreach (KeyValuePair<long, Color> eclat in eclats) { int r = rangs[eclat.Key] + 1; palette.SetPixel(r % LARGEUR_PALETTE, r / LARGEUR_PALETTE, eclat.Value); }
                if (marquee.HasValue && rangs.TryGetValue(marquee.Value, out int rang)) palette.SetPixel((rang + 1) % LARGEUR_PALETTE, (rang + 1) / LARGEUR_PALETTE, marque);
                palette.Apply(false);
            }
            Mesurer();
            if (frontieresAVerser) { frontieresAVerser = false; frontieres.SetPixelData(champ, 0); frontieres.Apply(false); }
            if (!paysAVerser) return;
            paysAVerser = false; paysDesCellules.SetPixelData(indices, 0); paysDesCellules.Apply(false); teintesDesPays.SetPixels(couleursDesPays); teintesDesPays.Apply(false);
        }
        // Mesure de nouveau les frontières là où une cellule a changé de pays ou quitté le dessin ; une cellule que le
        // terrain ne dessine pas n'en a pas et n'en fait pas.
        private void Mesurer() {
            if (!sale.HasValue) return;
            var pays = new int[posees.Length]; for (int r = 0; r < pays.Length; r++) pays[r] = posees[r] ? indices[r + 1] : -1;
            Terrain.Frontieres(pays, champ, sale.Value); sale = null; frontieresAVerser = true;
        }
        private void Salir(RectInt zone) {
            if (!sale.HasValue) { sale = zone; return; }
            RectInt s = sale.Value; int x0 = Mathf.Min(s.xMin, zone.xMin), y0 = Mathf.Min(s.yMin, zone.yMin);
            sale = new RectInt(x0, y0, Mathf.Max(s.xMax, zone.xMax) - x0, Mathf.Max(s.yMax, zone.yMax) - y0);
        }
        // Quand la table des pays est pleine, n'y garde que ceux qui tiennent encore une cellule : leurs indices se
        // resserrent, et deux cellules du même pays le restent.
        private void Tasser() {
            var neufs = new int[cles.Count]; var gardees = new List<string> { null }; var couleurs = new Color[couleursDesPays.Length];
            for (int c = 1; c < indices.Length; c++) {
                int ancien = indices[c]; if (ancien == 0) continue;
                if (neufs[ancien] == 0) { neufs[ancien] = gardees.Count; couleurs[gardees.Count] = couleursDesPays[ancien]; gardees.Add(cles[ancien]); }
                indices[c] = (ushort)neufs[ancien];
            }
            cles = gardees; couleursDesPays = couleurs; indicesDesPays.Clear(); paysAVerser = true;
            for (int k = 1; k < cles.Count; k++) indicesDesPays[cles[k]] = k;
        }
        // Un nom par ville servie, au-dessus du sol de sa place, lisible d'en haut, nord en haut.
        private void Nommer(CarteLue lue, PointCarte origine) {
            Transform villes = new GameObject("Villes de la carte").transform; villes.SetParent(transform, false);
            Font police = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            foreach (CelluleDeCarte cellule in lue.Cellules)
                foreach (VilleDeCarte ville in cellule.Villes) {
                    var nom = new GameObject("Ville " + ville.Nom).AddComponent<TextMesh>();
                    nom.transform.SetParent(villes, false); nom.transform.SetLocalPositionAndRotation(PositionSurLaCarte(ville.Position, HAUTEUR_NOM).Value, VERS_LE_BAS);
                    nom.font = police; nom.GetComponent<MeshRenderer>().sharedMaterial = police.material;
                    nom.fontSize = TAILLE_NOM; nom.characterSize = TAILLE_CARACTERE; nom.anchor = TextAnchor.MiddleCenter; nom.color = Color.black; nom.text = ville.Nom;
                }
        }
        private static Vector3 Place(PointCarte point, PointCarte origine, float hauteur) { Vector3 p = TriangulationDeCarte.Point(point.X, point.Y, origine); p.y = hauteur; return p; }
        // Seule la caméra créée est cadrée, sur la vue : une caméra donnée n'est jamais touchée. La toile du texte suit son plan proche.
        private void Cadrer() {
            if (Vue == null || camera == null) return;
            Vue.Changer(camera.aspect); Vue.Poser(camera, transform);
            if (toile != null) toile.planeDistance = camera.nearClipPlane + ECART_PLAN * camera.nearClipPlane;
        }
        private void Dire(string message) { if (texte == null) return; texte.text = message; texte.gameObject.SetActive(message != ""); }
    }
}
