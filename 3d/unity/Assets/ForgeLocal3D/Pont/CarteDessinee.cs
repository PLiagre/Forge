using System.Collections.Generic;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.UI;

namespace Forge.Pont {
    // La carte de 1400 servie par `sim/` : une cellule par objet, à la couleur de sa puissance, sans aucun
    // nombre calculé ici. Lecture et maillage partent hors du fil principal ; la pose se fait dans Update, une
    // seule fois. Sans carte, le texte dit pourquoi et rien n'est posé ; la lecture repart plus tard.
    public sealed class CarteDessinee : MonoBehaviour {
        public const string MESSAGE_ABSENCE = "le monde ne répond pas";
        public const float PERIODE_RELECTURE_S = 2f;
        private const string SANS_MATERIAU = "carte non dessinée : le pipeline de rendu n'a pas de matériau par défaut";
        private const float ECART_PLAN = 0.2f; private const int TAILLE_POLICE = 24;
        public int port = PanneauLieu.DEFAULT_SERVICE_PORT;
        public new Camera camera;
        private Text texte; private Transform racine; private ClientCarte client;
        private Task<(CarteMaillee carte, int servies, string absence)> enCours;
        private double prochaineLecture; private bool close; // carte posée, ou refusée faute de matériau : plus aucune lecture ne part
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
                if (lu.absence == null) Poser(lu.carte, lu.servies);
                else { Dire(MESSAGE_ABSENCE + "\n" + lu.absence); prochaineLecture = maintenant + PERIODE_RELECTURE_S; }
            }
            if (close || enCours != null || maintenant < prochaineLecture) return;
            ClientCarte lecteur = client; enCours = Task.Run(() => Lire(lecteur));
        }
        // Hors du fil principal : la carte servie, puis ses maillages ; une carte que le maillage refuse est une absence.
        private static (CarteMaillee, int, string) Lire(ClientCarte lecteur) {
            LectureCarte lecture = lecteur.Lire();
            if (!lecture.Presente) return (null, -1, lecture.Absence);
            try { return (MaillageDeCarte.Mailler(lecture.Carte), lecture.Carte.Cellules.Count, null); }
            catch (System.ArgumentException erreur) { return (null, -1, "carte : " + erreur.Message); }
        }
        private void Poser(CarteMaillee carte, int servies) {
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
                if (!materiaux.TryGetValue(cellule.Couleur, out Material materiau)) {
                    materiau = new Material(defaut) { name = "Couleur " + materiaux.Count, color = cellule.Couleur };
                    materiaux.Add(cellule.Couleur, materiau); crees.Add(materiau);
                }
                var objet = new GameObject("Cellule " + cellule.CellId, typeof(MeshFilter), typeof(MeshRenderer));
                objet.transform.SetParent(racine, false);
                objet.GetComponent<MeshFilter>().sharedMesh = maillage; objet.GetComponent<MeshRenderer>().sharedMaterial = materiau;
            }
            CellulesServies = servies; Dire("");
        }
        private void Dire(string message) { texte.text = message; texte.gameObject.SetActive(message != ""); }
    }
}
