using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.UI;

namespace Forge.Pont {
    // La carte de 1400 servie par `sim/` : un terrain en relief d'un seul tenant, levé de la carte (`GET /carte`) et de
    // la forme des lieux (`GET /formes`), où chaque lieu a sa teinte, au départ celle de la puissance de sa cellule,
    // sans aucun nombre du monde calculé ici. Lecture et levé du terrain partent hors du fil principal ; la pose se fait
    // dans Update, une seule fois. Sans carte ou sans formes, le texte dit pourquoi et rien n'est posé ; la lecture
    // repart plus tard. Une vue change la teinte d'une cellule par `Teinter`, celle d'un seul de ses lieux par
    // `TeinterLieu`, jamais par un objet. Les traits sont dessinés par le terrain lui-même, aux côtés servis : le bord de
    // chaque lieu, léger, qui s'efface quand la carte s'éloigne, la côte et ses lignes d'eau, et la frontière entre deux
    // lieux que `Rattacher` (toute une cellule) ou `RattacherLieu` (un lieu) donnent à des pays différents, doublée d'un
    // liseré à la couleur de chaque pays : elle passe dans une cellule quand deux pays se la partagent. Au départ,
    // chaque lieu est rattaché à la puissance servie de sa cellule.
    // Le terrain se dessine en relief : la mer est au niveau 0 de la carte, et les hauteurs du terrain levé y sont
    // réduites de `ECHELLE_DU_RELIEF`, pour qu'une montagne se voie sous une caméra inclinée sans cacher ce qui est
    // derrière elle. Tout ce qui se pose sur la carte se pose sur ce sol : `PositionSurLaCarte` rend un point à sa
    // hauteur au-dessus de lui, `Draper` une ligne qui le suit, `SolSous` le point du sol sous un point de l'écran.
    // Autour de la carte, le terrain trace un cadre, à `MARGE_DU_CADRE_KM` des cellules : au-delà, la table, d'une
    // couleur que `Encadrer` donne avec celle du filet. Tant qu'on ne l'encadre pas, la table est la mer et le filet
    // ne se voit pas.
    // Le nom de chaque ville, et sans caméra donnée, une à soi qui tient toute la carte.
    // Cette caméra montre la `Vue`, en perspective, que le joueur glisse et zoome (`ParcoursDeCarte`) sans sortir du cadre de la carte.
    public sealed class CarteDessinee : MonoBehaviour {
        public const string MESSAGE_ABSENCE = "le monde ne répond pas";
        public const float PERIODE_RELECTURE_S = 2f;
        public const float HAUTEUR_NOM = 1f;
        // Ce que le dessin garde des hauteurs du terrain levé ; et le pas, en km, d'une ligne drapée ou d'un rayon qui cherche le sol.
        public const float ECHELLE_DU_RELIEF = 0.3f, PAS_DU_DRAPE_KM = 6f, PAS_DU_RAYON_KM = 0.5f;
        // De combien le cadre s'écarte des cellules : assez pour laisser de la mer autour d'elles, moins que la marge de mer du terrain.
        public const float MARGE_DU_CADRE_KM = 70f;
        private const int PAS_MAX_DU_RAYON = 256, AFFINAGES = 12;
        public const string TERRAIN = "Terrain de la carte", SHADER_DU_TERRAIN = "Forge/CarteRelief";
        public const string NON_DESSINEE = "carte non dessinée : ";
        private const string SANS_SHADER = NON_DESSINEE + "shader " + SHADER_DU_TERRAIN + " absent";
        private const int LARGEUR_PALETTE = 256; // une teinte par lieu, rangée par lignes ; la case 0 est la mer, celle du lieu l est l + 1
        private const string PUISSANCE = "puissance "; // la clé du pays de départ d'une cellule : sa puissance servie
        private const float ECART_PLAN = 0.2f; private const int TAILLE_POLICE = 24;
        private const int TAILLE_NOM = 16; private const float TAILLE_CARACTERE = 25f; // une ligne de nom : environ 40 km, dessinée près de sa taille à l'écran
        private static readonly Color MER = new Color(0.08f, 0.16f, 0.3f), RIVAGE = new Color(0.2f, 0.3f, 0.42f), ROCHE = new Color(0.85f, 0.83f, 0.78f), BORD = new Color(0.1f, 0.08f, 0.06f), EAUX = new Color(0.5f, 0.6f, 0.7f);
        private static readonly Quaternion VERS_LE_BAS = Quaternion.Euler(90, 0, 0);
        public int port = PanneauLieu.DEFAULT_SERVICE_PORT;
        public new Camera camera;
        private Text texte; private Canvas toile; private ClientCarte client; private ClientFormes lecteurDesFormes;
        private Task<(CarteLue lue, FormesLues formes, TerrainDeCarte terrain, string absence)> enCours;
        private double prochaineLecture; private bool close; // carte posée, ou refusée faute de matériau : plus aucune lecture ne part
        private bool cameraCreee; private Bounds boite; // la boîte du cadre de la carte, en local : ce que la caméra créée cadre
        private readonly List<Object> crees = new List<Object>();
        private Material matiere; private Texture2D palette; private Color[] teintes; private bool aVerser; // la palette, une case par lieu, et si elle attend d'être versée au shader
        private Dictionary<long, int> rangs; private bool[] posees; private int nombrePosees; // le rang servi de chaque cellule, et celles que le terrain dessine
        private Color mer = MER, rivage = RIVAGE, roche = ROCHE, encreDesCotes = BORD, encreDesBords = BORD, encreDesFrontieres = BORD, encreDesEaux = EAUX;
        private Color? table; private Color filet = Color.clear; // la table d'autour de la carte (la mer, tant qu'on ne l'a pas donnée) et le filet du cadre
        // Les pays : la clé de chacun par indice (0 : aucun pays), l'indice du pays de chaque case de la palette (celle
        // d'un lieu), et la couleur du liseré de chaque pays. Les deux tables attendent d'être versées quand un
        // rattachement les change.
        private List<string> cles; private Dictionary<string, int> indicesDesPays; private ushort[] indices; private Color[] couleursDesPays;
        private Texture2D paysDesLieux, teintesDesPays; private bool paysAVerser;
        // Les distances aux frontières, un octet par texel ; le pays de chaque lieu à la dernière mesure (-1 : hors du
        // dessin), si un pays a pu changer depuis, la zone à mesurer de nouveau, et si la grille attend d'être versée.
        private Texture2D frontieres; private byte[] champ; private int[] mesures; private bool paysChanges; private RectInt? sale; private bool frontieresAVerser;
        private long? marquee; private Color marque; // la cellule marquée et la couleur qui couvre sa teinte
        private readonly Dictionary<long, Color> eclats = new Dictionary<long, Color>(); // les cellules éclairées et la couleur qui couvre leur teinte

        public string TexteAffiche => texte != null ? texte.text : null;
        public int CellulesServies { get; private set; } = -1;
        // Les cellules servies que le terrain dessine : celles qui ont au moins un texel et une teinte, et qu'on n'a pas retirées.
        public int CellulesPosees => nombrePosees;
        // Le terrain levé de la carte posée ; null avant la pose.
        public TerrainDeCarte Terrain { get; private set; }
        public bool LectureEnVol => enCours != null && !enCours.IsCompleted;
        // Combien de fois les frontières ont été mesurées de nouveau : seulement quand le pays d'un lieu a changé.
        public int MesuresDesFrontieres { get; private set; }
        public VueDeCarte Vue { get; private set; } // ce que la caméra créée montre ; null sans carte posée ou avec une caméra donnée
        private ReperageDeCarte reperage; // le lieu sous un point
        private PointCarte? origine; // l'origine de Mailler, gardée à la pose
        // La carte servie posée, la forme de ses lieux, et l'origine de ses km locaux : ce que les vues tirent des contours.
        // Nulles avant la pose.
        public CarteLue Lue { get; private set; }
        public FormesLues Formes { get; private set; }
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
        // La cellule servie sous un point du monde (à la verticale de la carte), celle du lieu qui le contient ; null dans
        // la mer ou sans carte posée.
        public CelluleDeCarte CelluleSous(Vector3 monde) {
            if (reperage == null) return null;
            Vector3 local = transform.InverseTransformPoint(monde); return reperage.Sous(local.x, local.z);
        }
        // La cellule et le rang du lieu sous un point du monde ; null dans la mer ou sans carte posée.
        public (CelluleDeCarte cellule, long rang)? LieuSous(Vector3 monde) {
            if (reperage == null) return null;
            Vector3 local = transform.InverseTransformPoint(monde); return reperage.LieuSous(local.x, local.z);
        }
        // Le rang servi d'une cellule que le terrain dessine.
        private bool Posee(long cellId, out int rang) {
            if (rangs != null && rangs.TryGetValue(cellId, out rang) && posees[rang]) return true;
            rang = -1; return false;
        }
        // Le lieu de ce rang d'une cellule que le terrain dessine ; -1 sinon.
        private int LieuPose(long cellId, long rangDuLieu) => Posee(cellId, out int rang) ? Terrain.LieuDe(rang, rangDuLieu) : -1;
        private IEnumerable<int> LieuxDe(int rang) { for (int l = Terrain.PremierLieuDe(rang); l < Terrain.PremierLieuDe(rang) + Terrain.LieuxDe(rang); l++) yield return l; }
        // La teinte dont une cellule posée est dessinée, celle de son lieu de rang 0 ; null si le terrain ne la dessine pas.
        public Color? TeinteDe(long cellId) => TeinteDuLieu(cellId, 0);
        // La teinte dont un lieu est dessiné ; null si le terrain ne le dessine pas.
        public Color? TeinteDuLieu(long cellId, long rang) { int l = LieuPose(cellId, rang); return l < 0 ? (Color?)null : teintes[l + 1]; }
        // Dessine tous les lieux d'une cellule posée d'une autre teinte ; faux si le terrain ne la dessine pas.
        public bool Teinter(long cellId, Color teinte) {
            if (!Posee(cellId, out int rang)) return false;
            foreach (int l in LieuxDe(rang)) Peindre(l, teinte);
            return true;
        }
        // Dessine un seul lieu d'une autre teinte ; les autres lieux de sa cellule gardent la leur. Faux si le terrain ne le dessine pas.
        public bool TeinterLieu(long cellId, long rang, Color teinte) {
            int l = LieuPose(cellId, rang); if (l < 0) return false;
            Peindre(l, teinte); return true;
        }
        private void Peindre(int lieu, Color teinte) { teinte.a = 1f; if (teintes[lieu + 1] != teinte) { teintes[lieu + 1] = teinte; aVerser = true; } }
        // Retire une cellule du dessin : le sol de ses lieux rend la mer, elle perd sa marque et ne compte plus parmi les posées.
        public bool Retirer(long cellId) {
            if (!Posee(cellId, out int rang)) return false;
            posees[rang] = false; nombrePosees--; foreach (int l in LieuxDe(rang)) teintes[l + 1] = Color.clear;
            if (marquee == cellId) marquee = null; eclats.Remove(cellId); aVerser = true;
            paysChanges = true; return true; // ses voisins n'ont plus de frontière avec elle
        }
        // Rattache tous les lieux d'une cellule posée à un pays, nommé par sa clé, et donne au pays la couleur de son
        // liseré ; sans clé, ils ne sont à aucun pays. Une frontière sépare deux lieux voisins qui ne sont pas au même
        // pays. Faux si le terrain ne la dessine pas.
        public bool Rattacher(long cellId, string pays, Color couleur) {
            if (!Posee(cellId, out int rang)) return false;
            Rattacher(LieuxDe(rang).ToArray(), pays, couleur); return true;
        }
        // Rattache un seul lieu d'une cellule posée ; les autres lieux de sa cellule gardent leur pays. Faux si le terrain
        // ne le dessine pas.
        public bool RattacherLieu(long cellId, long rang, string pays, Color couleur) {
            int l = LieuPose(cellId, rang); if (l < 0) return false;
            Rattacher(new[] { l }, pays, couleur); return true;
        }
        private void Rattacher(int[] lieux, string pays, Color couleur) {
            int indice = 0;
            if (!string.IsNullOrEmpty(pays) && !indicesDesPays.TryGetValue(pays, out indice)) {
                if (cles.Count == couleursDesPays.Length) { foreach (int l in lieux) indices[l + 1] = 0; Tasser(); }
                indice = cles.Count; cles.Add(pays); indicesDesPays[pays] = indice;
            }
            couleur.a = 1f;
            if (indice > 0 && couleursDesPays[indice] != couleur) { couleursDesPays[indice] = couleur; paysAVerser = true; }
            foreach (int l in lieux) if (indices[l + 1] != indice) { indices[l + 1] = (ushort)indice; paysAVerser = true; paysChanges = true; }
        }
        // La clé du pays d'une cellule posée, celui de son lieu de rang 0 ; null si elle n'est à aucun pays ou que le terrain ne la dessine pas.
        public string PaysDe(long cellId) => PaysDuLieu(cellId, 0);
        // La clé du pays d'un lieu ; null s'il n'est à aucun pays ou que le terrain ne le dessine pas.
        public string PaysDuLieu(long cellId, long rang) { int l = LieuPose(cellId, rang); return l < 0 ? null : cles[indices[l + 1]]; }
        // Sous un point en km locaux, la distance en km à la plus proche frontière du pays qui tient ce point, telle
        // que le terrain la dessine ; la portée des frontières quand elle est plus loin, en mer ou sans frontière ;
        // -1 sans carte posée.
        public float DistanceALaFrontiere(float x, float z) {
            if (champ == null) return -1f;
            Mesurer(); return Terrain.FrontiereEn(champ, x, z);
        }
        // Les encres des traits du terrain : la côte, le bord des lieux, les frontières, les lignes d'eau.
        public void Encrer(Color cotes, Color bords, Color desFrontieres, Color eaux) {
            encreDesCotes = cotes; encreDesBords = bords; encreDesFrontieres = desFrontieres; encreDesEaux = eaux;
            if (matiere == null) return;
            matiere.SetColor("_EncreDesCotes", cotes); matiere.SetColor("_EncreDesBords", bords); matiere.SetColor("_EncreDesFrontieres", desFrontieres); matiere.SetColor("_EncreDesEaux", eaux);
        }
        // Les pays se voient-ils sur le terrain : leur liseré et leurs frontières. Éteints, le terrain se montre nu, et les
        // rattachements restent : rien ne se remesure, et les frontières reviennent telles quelles.
        public bool PaysMontres { get; private set; } = true;
        public void MontrerLesPays(bool montres) {
            PaysMontres = montres;
            if (matiere != null) matiere.SetFloat("_ForceDesPays", montres ? 1f : 0f);
        }
        // La cellule marquée, ou null : une seule à la fois.
        public long? Marquee => marquee;
        // Couvre tous les lieux d'une cellule posée d'une couleur sans toucher à leur teinte, qui revient quand la marque
        // part ; faux si le terrain ne la dessine pas, et la marque d'avant reste.
        public bool Marquer(long cellId, Color couleur) {
            if (!Posee(cellId, out _)) return false;
            couleur.a = 1f; marquee = cellId; marque = couleur; aVerser = true; return true;
        }
        public void Demarquer() { if (marquee.HasValue) { marquee = null; aVerser = true; } }
        // Éclaire une cellule posée : comme la marque, la couleur couvre la teinte de ses lieux sans y toucher, et le
        // relief, les bords et les frontières s'y dessinent toujours. Autant de cellules qu'on veut ; la marque passe
        // devant. Faux si le terrain ne la dessine pas.
        public bool Eclairer(long cellId, Color couleur) {
            if (!Posee(cellId, out _)) return false;
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
            if (!table.HasValue) matiere.SetColor("_Table", mer); // sans table donnée, la mer continue au-delà du cadre
        }
        // Le cadre de la carte, en km locaux : la boîte des cellules, élargie de `MARGE_DU_CADRE_KM` ; vide avant la pose.
        public Rect Cadre { get; private set; }
        // Les couleurs du bord de la carte : la table au-delà du cadre, qui est aussi le fond de la caméra, et le filet du cadre.
        public void Encadrer(Color laTable, Color leFilet) {
            laTable.a = 1f; table = laTable; filet = leFilet;
            if (camera != null) camera.backgroundColor = laTable;
            if (matiere == null) return;
            matiere.SetColor("_Table", laTable); matiere.SetColor("_Filet", leFilet);
        }
        // Pose une carte et ses formes déjà lues, sans service : le terrain se lève sur place. Sans effet sur une carte déjà posée.
        public void Montrer(CarteLue lue, FormesLues formes) { if (!close) Poser(lue, formes, TerrainDeCarte.Lever(lue, formes)); }
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
            client = new ClientCarte(port, ClientCarte.DelaiMinimal); lecteurDesFormes = new ClientFormes(port, ClientFormes.DelaiMinimal);
        }
        public void Arreter() {
            client?.Dispose(); client = null; lecteurDesFormes?.Dispose(); lecteurDesFormes = null; enCours = null;
            foreach (Object o in crees) if (Application.isPlaying) Destroy(o); else DestroyImmediate(o);
            crees.Clear();
        }
        public void Pas(double maintenant) {
            if (client == null) return;
            if (enCours != null && enCours.IsCompleted) {
                var lu = enCours.Result; enCours = null;
                if (lu.absence == null) Poser(lu.lue, lu.formes, lu.terrain);
                else { Dire(lu.absence); prochaineLecture = maintenant + PERIODE_RELECTURE_S; }
            }
            Cadrer(); // la fenêtre peut avoir changé de forme
            Verser();
            if (close || enCours != null || maintenant < prochaineLecture) return;
            ClientCarte lecteur = client; ClientFormes desLieux = lecteurDesFormes; enCours = Task.Run(() => Lire(lecteur, desLieux));
        }
        // Hors du fil principal : la carte servie, la forme de ses lieux, puis son terrain. Sans carte, le monde ne répond
        // pas ; sans formes, ou des formes que le levé refuse, la carte dit pourquoi elle ne se dessine pas, et ne se
        // dessine jamais sans elles. Le journal dit ce qu'a pris chaque temps : la lecture de la carte, celle des formes,
        // et le levé du terrain.
        private static (CarteLue, FormesLues, TerrainDeCarte, string) Lire(ClientCarte lecteur, ClientFormes desLieux) {
            var montre = System.Diagnostics.Stopwatch.StartNew();
            LectureCarte lecture = lecteur.Lire();
            if (!lecture.Presente) return (null, null, null, MESSAGE_ABSENCE + "\n" + lecture.Absence);
            long carte = montre.ElapsedMilliseconds;
            LectureFormes formes = desLieux.Lire();
            if (!formes.Presente) return (null, null, null, NON_DESSINEE + formes.Absence);
            long lues = montre.ElapsedMilliseconds;
            try {
                TerrainDeCarte terrain = TerrainDeCarte.Lever(lecture.Carte, formes.Formes);
                Debug.Log("CARTE : /carte lue en " + carte + " ms, /formes en " + (lues - carte) + " ms, terrain de " + terrain.NombreDeLieux + " lieux levé en "
                    + (montre.ElapsedMilliseconds - lues) + " ms (" + terrain.Largeur + " × " + terrain.Hauteur + " texels au pas de " + terrain.Pas.ToString("0.###", System.Globalization.CultureInfo.InvariantCulture) + " km)");
                return (lecture.Carte, formes.Formes, terrain, null);
            }
            catch (System.ArgumentException erreur) { return (null, null, null, NON_DESSINEE + "formes : " + erreur.Message); }
        }
        private void Poser(CarteLue lue, FormesLues formes, TerrainDeCarte terrain) {
            close = true;
            Shader relief = Resources.Load<Shader>(SHADER_DU_TERRAIN);
            if (relief == null) { Dire(SANS_SHADER); return; }
            var maillage = new Mesh { name = TERRAIN, indexFormat = IndexFormat.UInt32 };
            maillage.SetVertices(terrain.SommetsDuMaillage); maillage.SetUVs(0, terrain.UvDuMaillage); maillage.SetTriangles(terrain.TrianglesDuMaillage, 0);
            maillage.RecalculateBounds(); crees.Add(maillage);
            // Les numéros des lieux et les distances se lisent au texel près ; le relief se lit entre ses altitudes.
            Texture2D lieux = Creer("Lieux de la carte", terrain.Largeur, terrain.Hauteur, TextureFormat.R16, FilterMode.Point, true);
            lieux.SetPixelData(terrain.TexelsDesLieux, 0); lieux.Apply(false, true);
            Texture2D altitudes = Creer("Relief de la carte", terrain.LargeurDuRelief, terrain.HauteurDuRelief, TextureFormat.RFloat, FilterMode.Bilinear, true);
            altitudes.SetPixelData(terrain.TexelsDuRelief, 0); altitudes.Apply(false, true);
            Texture2D bords = Creer("Bords de la carte", terrain.Largeur, terrain.Hauteur, TextureFormat.RG16, FilterMode.Point, true);
            bords.SetPixelData(terrain.TexelsDesBords, 0); bords.Apply(false, true);
            frontieres = Creer("Frontières de la carte", terrain.Largeur, terrain.Hauteur, TextureFormat.R8, FilterMode.Point, true);
            champ = new byte[terrain.Largeur * terrain.Hauteur]; Terrain = terrain; mesures = null; paysChanges = true;
            int servies = lue.Cellules.Count;
            palette = Creer("Teintes de la carte", LARGEUR_PALETTE, (terrain.NombreDeLieux + LARGEUR_PALETTE) / LARGEUR_PALETTE, TextureFormat.RGBA32, FilterMode.Point, false);
            teintes = new Color[palette.width * palette.height]; rangs = new Dictionary<long, int>(servies); posees = new bool[servies]; nombrePosees = 0;
            // Les deux tables des pays se rangent comme la palette : la case d'un lieu dit son pays, celle d'un pays sa couleur.
            paysDesLieux = Creer("Pays des lieux", palette.width, palette.height, TextureFormat.R16, FilterMode.Point, true);
            teintesDesPays = Creer("Teintes des pays", palette.width, palette.height, TextureFormat.RGBA32, FilterMode.Point, false);
            indices = new ushort[teintes.Length]; couleursDesPays = new Color[teintes.Length]; cles = new List<string> { null }; indicesDesPays = new Dictionary<string, int>();
            for (int rang = 0; rang < servies; rang++) {
                CelluleDeCarte cellule = lue.Cellules[rang]; rangs[cellule.CellId] = rang;
                if (terrain.TexelsDe(rang) == 0) continue; // sans texel, rien ne la dessine
                Color teinte = MaillageDeCarte.CouleurDe(cellule); teinte.a = 1f; foreach (int l in LieuxDe(rang)) teintes[l + 1] = teinte; posees[rang] = true; nombrePosees++;
                if (cellule.Puissance != null) Rattacher(cellule.CellId, PUISSANCE + cellule.Puissance.Id, teinte);
            }
            matiere = new Material(relief) { name = TERRAIN }; crees.Add(matiere);
            matiere.SetTexture("_Lieux", lieux); matiere.SetTexture("_Relief", altitudes); matiere.SetTexture("_Palette", palette);
            matiere.SetTexture("_Bords", bords); matiere.SetTexture("_Frontieres", frontieres); matiere.SetTexture("_Pays", paysDesLieux); matiere.SetTexture("_TeintesDesPays", teintesDesPays);
            matiere.SetFloat("_PasDuRelief", terrain.PasDuRelief); matiere.SetFloat("_Fond", TerrainDeCarte.FOND); matiere.SetFloat("_Plafond", TerrainDeCarte.PLAFOND);
            matiere.SetFloat("_Pas", terrain.Pas); matiere.SetFloat("_PorteeDesBords", TerrainDeCarte.PORTEE_DES_BORDS_KM); matiere.SetFloat("_PorteeDesFrontieres", TerrainDeCarte.PORTEE_DES_FRONTIERES_KM);
            // Le cadre, dans les km du terrain : depuis son coin du sud-ouest.
            Vector2 coin = terrain.Coin; Bounds terres = terrain.Boite;
            Cadre = Rect.MinMaxRect(terres.min.x - MARGE_DU_CADRE_KM, terres.min.z - MARGE_DU_CADRE_KM, terres.max.x + MARGE_DU_CADRE_KM, terres.max.z + MARGE_DU_CADRE_KM);
            matiere.SetVector("_Cadre", new Vector4(Cadre.xMin - coin.x, Cadre.yMin - coin.y, Cadre.xMax - coin.x, Cadre.yMax - coin.y));
            matiere.SetColor("_Table", table ?? mer); matiere.SetColor("_Filet", filet);
            Habiller(mer, rivage, roche); Encrer(encreDesCotes, encreDesBords, encreDesFrontieres, encreDesEaux); MontrerLesPays(PaysMontres); aVerser = true; paysAVerser = true; Verser();
            // Le maillage levé a sa plus haute cime au plan 0 : il se pose de façon que la mer soit au niveau 0 de la carte, ses hauteurs réduites.
            var sol = new GameObject(TERRAIN, typeof(MeshFilter), typeof(MeshRenderer)); sol.transform.SetParent(transform, false);
            sol.transform.localPosition = new Vector3(0f, TerrainDeCarte.PLAFOND * ECHELLE_DU_RELIEF, 0f); sol.transform.localScale = new Vector3(1f, ECHELLE_DU_RELIEF, 1f);
            sol.GetComponent<MeshFilter>().sharedMesh = maillage;
            var rendu = sol.GetComponent<MeshRenderer>(); rendu.sharedMaterial = matiere; rendu.shadowCastingMode = ShadowCastingMode.Off; rendu.receiveShadows = false;
            // La vue tient toute la planche : les cellules et le cadre autour d'elles.
            boite = new Bounds(); boite.SetMinMax(new Vector3(Cadre.xMin, 0f, Cadre.yMin), new Vector3(Cadre.xMax, 0f, Cadre.yMax));
            origine = terrain.Origine; Nommer(lue, terrain.Origine); reperage = new ReperageDeCarte(lue, formes, terrain.Origine); Lue = lue; Formes = formes;
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
                foreach (KeyValuePair<long, Color> eclat in eclats) Couvrir(rangs[eclat.Key], eclat.Value);
                if (marquee.HasValue && rangs.TryGetValue(marquee.Value, out int rang)) Couvrir(rang, marque);
                palette.Apply(false);
            }
            Mesurer();
            if (frontieresAVerser) { frontieresAVerser = false; frontieres.SetPixelData(champ, 0); frontieres.Apply(false); }
            if (!paysAVerser) return;
            paysAVerser = false; paysDesLieux.SetPixelData(indices, 0); paysDesLieux.Apply(false); teintesDesPays.SetPixels(couleursDesPays); teintesDesPays.Apply(false);
        }
        // Couvre dans la palette les cases de tous les lieux d'une cellule.
        private void Couvrir(int rang, Color couleur) { foreach (int l in LieuxDe(rang)) palette.SetPixel((l + 1) % LARGEUR_PALETTE, (l + 1) / LARGEUR_PALETTE, couleur); }
        // Mesure de nouveau les frontières autour des seuls lieux dont le pays a changé depuis la dernière mesure, ou qui
        // ont quitté le dessin : un rattachement qui rend à un lieu le pays qu'il avait ne remesure rien. Un lieu que le
        // terrain ne dessine pas n'a pas de frontière et n'en fait pas.
        private void Mesurer() {
            if (!paysChanges) return;
            paysChanges = false;
            var pays = new int[Terrain.NombreDeLieux];
            for (int l = 0; l < pays.Length; l++) pays[l] = posees[Terrain.CelluleDuLieu(l)] ? indices[l + 1] : -1;
            if (mesures == null) sale = Terrain.Tout;
            else for (int l = 0; l < pays.Length; l++) if (pays[l] != mesures[l]) Salir(Terrain.ZoneDuLieu(l));
            mesures = pays;
            if (!sale.HasValue) return;
            Terrain.Frontieres(pays, champ, sale.Value); sale = null; frontieresAVerser = true; MesuresDesFrontieres++;
        }
        private void Salir(RectInt zone) {
            if (!sale.HasValue) { sale = zone; return; }
            RectInt s = sale.Value; int x0 = Mathf.Min(s.xMin, zone.xMin), y0 = Mathf.Min(s.yMin, zone.yMin);
            sale = new RectInt(x0, y0, Mathf.Max(s.xMax, zone.xMax) - x0, Mathf.Max(s.yMax, zone.yMax) - y0);
        }
        // Quand la table des pays est pleine, n'y garde que ceux qui tiennent encore un lieu : leurs indices se
        // resserrent, et deux lieux du même pays le restent. La dernière mesure suit le resserrement ; un pays qui n'est
        // plus tenu y prend une valeur qu'aucun lieu n'a, pour que ses anciens lieux se remesurent.
        private void Tasser() {
            var neufs = new int[cles.Count]; var gardees = new List<string> { null }; var couleurs = new Color[couleursDesPays.Length];
            for (int c = 1; c < indices.Length; c++) {
                int ancien = indices[c]; if (ancien == 0) continue;
                if (neufs[ancien] == 0) { neufs[ancien] = gardees.Count; couleurs[gardees.Count] = couleursDesPays[ancien]; gardees.Add(cles[ancien]); }
                indices[c] = (ushort)neufs[ancien];
            }
            if (mesures != null) for (int l = 0; l < mesures.Length; l++) if (mesures[l] > 0) mesures[l] = neufs[mesures[l]] > 0 ? neufs[mesures[l]] : -2;
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
