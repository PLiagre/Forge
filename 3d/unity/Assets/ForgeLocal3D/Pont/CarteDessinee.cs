using System.Collections.Generic;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.UI;

namespace Forge.Pont {
    // La carte de 1400 servie par `sim/` : une cellule par objet, à la couleur de sa puissance, sans aucun
    // nombre calculé ici. Lecture et maillage partent hors du fil principal ; la pose se fait dans Update, une
    // seule fois. Sans carte, le texte dit pourquoi et rien n'est posé ; la lecture repart plus tard.
    // Lot #548 : le bord de chaque anneau, le nom de chaque ville, et sans caméra donnée, une à soi qui tient toute la carte.
    public sealed class CarteDessinee : MonoBehaviour {
        public const string MESSAGE_ABSENCE = "le monde ne répond pas";
        public const float PERIODE_RELECTURE_S = 2f;
        public const float HAUTEUR_CONTOUR = 0.5f, LARGEUR_CONTOUR = 4f, HAUTEUR_NOM = 1f, HAUTEUR_CAMERA = 1000f;
        private const string SANS_MATERIAU = "carte non dessinée : le pipeline de rendu n'a pas de matériau par défaut";
        private const float ECART_PLAN = 0.2f, PROCHE = 1f, LOINTAIN = 2000f, MARGE_CADRE = 1.03f; private const int TAILLE_POLICE = 24;
        private const int TAILLE_NOM = 16; private const float TAILLE_CARACTERE = 25f; // une ligne de nom : environ 40 km, dessinée près de sa taille à l'écran
        private static readonly Color MER = new Color(0.08f, 0.16f, 0.3f), BORD = new Color(0.1f, 0.08f, 0.06f); private static readonly Quaternion VERS_LE_BAS = Quaternion.Euler(90, 0, 0);
        public int port = PanneauLieu.DEFAULT_SERVICE_PORT;
        public new Camera camera;
        private Text texte; private Transform racine; private ClientCarte client;
        private Task<(CarteLue lue, CarteMaillee carte, string absence)> enCours;
        private double prochaineLecture; private bool close; // carte posée, ou refusée faute de matériau : plus aucune lecture ne part
        private bool cameraCreee; private Bounds boite; // la boîte des cellules, en local : ce que la caméra créée cadre
        private readonly List<Object> crees = new List<Object>();

        public string TexteAffiche => texte != null ? texte.text : null;
        public int CellulesServies { get; private set; } = -1;
        public int CellulesPosees => racine != null ? racine.childCount : 0;
        public bool LectureEnVol => enCours != null && !enCours.IsCompleted;
        private void Start() => Demarrer();
        private void Update() => Pas(Time.realtimeSinceStartupAsDouble);
        private void OnDestroy() => Arreter();
        // Sur la caméra posée, comme PanneauLieu, juste derrière son plan proche : la capture voit le texte.
        public void Demarrer() {
            if (camera == null) { // la sienne, vue de la mer, cadrée une fois la carte posée
                camera = new GameObject("Caméra de la carte").AddComponent<Camera>(); camera.transform.SetParent(transform, false); cameraCreee = true;
                camera.orthographic = true; camera.clearFlags = CameraClearFlags.SolidColor; camera.backgroundColor = MER; camera.nearClipPlane = PROCHE; camera.farClipPlane = LOINTAIN;
            }
            var toile = new GameObject("Toile de la carte", typeof(RectTransform)).AddComponent<Canvas>();
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
                if (lu.absence == null) Poser(lu.lue, lu.carte);
                else { Dire(MESSAGE_ABSENCE + "\n" + lu.absence); prochaineLecture = maintenant + PERIODE_RELECTURE_S; }
            }
            Cadrer(); // la fenêtre peut avoir changé de forme
            if (close || enCours != null || maintenant < prochaineLecture) return;
            ClientCarte lecteur = client; enCours = Task.Run(() => Lire(lecteur));
        }
        // Hors du fil principal : la carte servie, puis ses maillages ; une carte que le maillage refuse est une absence.
        private static (CarteLue, CarteMaillee, string) Lire(ClientCarte lecteur) {
            LectureCarte lecture = lecteur.Lire();
            if (!lecture.Presente) return (null, null, lecture.Absence);
            try { return (lecture.Carte, MaillageDeCarte.Mailler(lecture.Carte), null); }
            catch (System.ArgumentException erreur) { return (null, null, "carte : " + erreur.Message); }
        }
        private void Poser(CarteLue lue, CarteMaillee carte) {
            close = true;
            RenderPipelineAsset pipeline = GraphicsSettings.currentRenderPipeline;
            Material defaut = pipeline != null ? pipeline.defaultMaterial : null;
            if (defaut == null) { Dire(SANS_MATERIAU); return; }
            racine = new GameObject("Cellules de la carte").transform; racine.SetParent(transform, false);
            var materiaux = new Dictionary<Color, Material>(); // un par couleur, jamais par rang
            foreach (MaillageDeCellule cellule in carte.Cellules) {
                var maillage = new Mesh { name = "Cellule " + cellule.CellId };
                maillage.SetVertices(new List<Vector3>(cellule.Maillage.Sommets));
                maillage.SetTriangles(new List<int>(cellule.Maillage.Triangles), 0);
                maillage.RecalculateNormals(); maillage.RecalculateBounds(); crees.Add(maillage);
                if (racine.childCount == 0) boite = maillage.bounds; else boite.Encapsulate(maillage.bounds);
                if (!materiaux.TryGetValue(cellule.Couleur, out Material materiau)) {
                    materiau = new Material(defaut) { name = "Couleur " + materiaux.Count, color = cellule.Couleur };
                    materiaux.Add(cellule.Couleur, materiau); crees.Add(materiau);
                }
                var objet = new GameObject("Cellule " + cellule.CellId, typeof(MeshFilter), typeof(MeshRenderer));
                objet.transform.SetParent(racine, false);
                objet.GetComponent<MeshFilter>().sharedMesh = maillage; objet.GetComponent<MeshRenderer>().sharedMaterial = materiau;
            }
            Tracer(lue, carte.Origine, defaut); Nommer(lue, carte.Origine);
            CellulesServies = lue.Cellules.Count; Dire(""); Cadrer();
        }
        // Un trait par anneau servi, déjà fermé : l'extérieur de chaque polygone, puis ses trous.
        private void Tracer(CarteLue lue, PointCarte origine, Material defaut) {
            Transform bords = new GameObject("Contours de la carte").transform; bords.SetParent(transform, false);
            var sombre = new Material(defaut) { name = "Contour", color = BORD }; crees.Add(sombre);
            foreach (CelluleDeCarte cellule in lue.Cellules) {
                int rang = 0;
                foreach (PolygoneDeCarte polygone in cellule.Contour)
                    for (int a = -1; a < polygone.Trous.Count; a++) {
                        IReadOnlyList<PointCarte> anneau = a < 0 ? polygone.Exterieur : polygone.Trous[a];
                        var trait = new GameObject("Contour " + cellule.CellId + "." + rang++).AddComponent<LineRenderer>(); trait.transform.SetParent(bords, false);
                        trait.useWorldSpace = false; trait.loop = false; trait.widthMultiplier = LARGEUR_CONTOUR; trait.sharedMaterial = sombre; trait.shadowCastingMode = ShadowCastingMode.Off;
                        var points = new Vector3[anneau.Count]; for (int k = 0; k < points.Length; k++) points[k] = Place(anneau[k], origine, HAUTEUR_CONTOUR);
                        trait.positionCount = points.Length; trait.SetPositions(points);
                    }
            }
        }
        // Un nom par ville servie, à sa place, lisible d'en haut, nord en haut.
        private void Nommer(CarteLue lue, PointCarte origine) {
            Transform villes = new GameObject("Villes de la carte").transform; villes.SetParent(transform, false);
            Font police = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            foreach (CelluleDeCarte cellule in lue.Cellules)
                foreach (VilleDeCarte ville in cellule.Villes) {
                    var nom = new GameObject("Ville " + ville.Nom).AddComponent<TextMesh>();
                    nom.transform.SetParent(villes, false); nom.transform.SetLocalPositionAndRotation(Place(ville.Position, origine, HAUTEUR_NOM), VERS_LE_BAS);
                    nom.font = police; nom.GetComponent<MeshRenderer>().sharedMaterial = police.material;
                    nom.fontSize = TAILLE_NOM; nom.characterSize = TAILLE_CARACTERE; nom.anchor = TextAnchor.MiddleCenter; nom.color = Color.black; nom.text = ville.Nom;
                }
        }
        private static Vector3 Place(PointCarte point, PointCarte origine, float hauteur) { Vector3 p = TriangulationDeCarte.Point(point.X, point.Y, origine); p.y = hauteur; return p; }
        // Seule la caméra créée est cadrée : une caméra donnée n'est jamais touchée.
        private void Cadrer() {
            if (!cameraCreee || racine == null || camera == null) return;
            camera.transform.SetPositionAndRotation(transform.TransformPoint(new Vector3(boite.center.x, HAUTEUR_CAMERA, boite.center.z)), VERS_LE_BAS);
            camera.orthographicSize = Mathf.Max(boite.extents.z, boite.extents.x / camera.aspect) * MARGE_CADRE;
        }
        private void Dire(string message) { texte.text = message; texte.gameObject.SetActive(message != ""); }
    }
}
