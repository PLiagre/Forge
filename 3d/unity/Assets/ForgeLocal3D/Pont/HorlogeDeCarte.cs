using System;
using System.Globalization;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Pont {
    // Lot #525 : la date du monde sur la carte, et l'horloge que le joueur règle. Le panneau relit `/horloge` toutes les
    // `PERIODE_LECTURE_S` : la date, le tick et la vitesse sont ceux que le service rend, jamais avancés ni calculés ici.
    // Le joueur met en pause, relance, accélère ou ralentit (les boutons du panneau, ou Espace, + et − par
    // `CommandesDuTemps`) ; la vitesse part au service (`POST /vitesse`), et le panneau affiche celle qu'il rend. Une
    // requête à la fois, hors du fil principal ; une vitesse demandée pendant une lecture part juste après. Sans service,
    // le panneau le dit, et aucune vitesse ne part : on ne règle pas un temps qu'on ne connaît pas.
    [DefaultExecutionOrder(10)] // après CarteDessinee, dont il prend la caméra créée
    public sealed class HorlogeDeCarte : MonoBehaviour {
        public const float PERIODE_LECTURE_S = 0.25f;
        public static readonly double[] PALIERS = { 0.5, 1, 2, 5, 10, 20 }; // jours par seconde
        public const double VITESSE_DE_REPRISE = 1; // si le monde était déjà en pause quand la carte s'est ouverte
        private static readonly TimeSpan DELAI = TimeSpan.FromSeconds(2);
        private static readonly Vector2 RESOLUTION_REFERENCE = new Vector2(1600, 900);
        private static readonly Color FOND = new Color(0.05f, 0.05f, 0.07f, 0.78f), BOUTON = new Color(0.22f, 0.24f, 0.3f, 1f);
        private const float ECART_PLAN = 0.2f, MARGE = 16f; private const int RETRAIT = 12, TAILLE_POLICE = 24;

        public int port = PanneauLieu.DEFAULT_SERVICE_PORT;
        public new Camera camera; // vide : celle de la CarteDessinee du même objet

        private ClientHorloge client; private Text texte, libellePause;
        private Task<Lecture<HorlogeLue>> enCours; private double? vitesseDemandee;
        private double prochaineLecture, vitesseDeReprise = VITESSE_DE_REPRISE;
        private GameObject toile;

        public HorlogeLue Lue { get; private set; } // la dernière horloge servie ; null tant qu'aucune ne l'est
        public string Absence { get; private set; } // la cause de la dernière lecture manquée ; null après une lecture servie
        public string TexteAffiche => texte != null ? texte.text : null;
        public bool RequeteEnVol => enCours != null && !enCours.IsCompleted;

        private void Start() { var carte = GetComponent<CarteDessinee>(); Demarrer(camera != null ? camera : carte != null ? carte.camera : null); }
        private void Update() => Pas(Time.realtimeSinceStartupAsDouble);
        private void OnDestroy() => Arreter();

        public void Demarrer(Camera vue) {
            camera = vue;
            if (camera == null) { Debug.LogError("HorlogeDeCarte : pas de caméra, le panneau ne s'affiche pas", this); return; }
            Construire();
            Dire("horloge : en attente de 127.0.0.1:" + port);
            client = new ClientHorloge(port, DELAI);
        }

        public void Arreter() { client?.Dispose(); client = null; enCours = null; if (toile != null) Detruire(toile); toile = null; }

        public void Pas(double maintenant) {
            if (client == null) return;
            if (enCours != null && enCours.IsCompleted) { Appliquer(enCours.Result); enCours = null; }
            if (enCours != null) return;
            ClientHorloge c = client;
            if (vitesseDemandee is double v) { vitesseDemandee = null; enCours = Task.Run(() => c.Regler(v)); return; }
            if (maintenant < prochaineLecture) return;
            prochaineLecture = maintenant + PERIODE_LECTURE_S;
            enCours = Task.Run(() => c.Lire());
        }

        // Pause si le monde avance ; sinon, il repart à la vitesse qu'il avait.
        public void Basculer() {
            if (Lue == null) return;
            if (Lue.JoursParSeconde > 0) { vitesseDeReprise = Lue.JoursParSeconde; Demander(0); }
            else Demander(vitesseDeReprise);
        }
        public void Accelerer() { if (Lue != null) Demander(Suivante(Lue.JoursParSeconde, +1)); }
        public void Ralentir() { if (Lue != null) Demander(Suivante(Lue.JoursParSeconde, -1)); }

        // Le palier au-dessus (sens > 0) ou au-dessous de la vitesse servie, borné aux paliers ; jamais la pause.
        public static double Suivante(double actuelle, int sens) {
            if (sens > 0) { foreach (double p in PALIERS) if (p > actuelle) return p; return PALIERS[PALIERS.Length - 1]; }
            for (int i = PALIERS.Length - 1; i >= 0; i--) if (PALIERS[i] < actuelle) return PALIERS[i];
            return PALIERS[0];
        }

        public static string Decrire(HorlogeLue h) =>
            "Jour " + Entier(h.Date.JourDeLAnnee) + " de " + Entier(h.Date.Annee) + " · tick " + Entier(h.Tick) + "\n"
            + (h.JoursParSeconde == 0 ? "En pause" : Nombre(h.JoursParSeconde) + (h.JoursParSeconde >= 2 ? " jours" : " jour") + " par seconde");

        private void Demander(double joursParSeconde) => vitesseDemandee = joursParSeconde;

        private void Appliquer(Lecture<HorlogeLue> lecture) {
            if (!lecture.Presente) { Absence = lecture.Absence; Dire(CarteDessinee.MESSAGE_ABSENCE + "\n" + lecture.Absence); return; }
            Lue = lecture.Donnees; Absence = null; Dire(Decrire(Lue));
            if (Lue.JoursParSeconde > 0) vitesseDeReprise = Lue.JoursParSeconde;
            libellePause.text = Lue.JoursParSeconde > 0 ? "Pause" : "Reprendre";
        }

        private void Dire(string message) { if (texte != null) texte.text = message; }

        private static string Entier(long v) => v.ToString(CultureInfo.InvariantCulture);
        private static string Nombre(double v) => v.ToString("R", CultureInfo.InvariantCulture);

        // En haut à droite de l'écran, sur la caméra : la date et la vitesse, puis trois boutons.
        private void Construire() {
            toile = new GameObject("Toile de l'horloge", typeof(RectTransform));
            toile.transform.SetParent(transform, false);
            var canvas = toile.AddComponent<Canvas>(); canvas.renderMode = RenderMode.ScreenSpaceCamera; canvas.worldCamera = camera;
            canvas.planeDistance = camera.nearClipPlane + ECART_PLAN; canvas.sortingOrder = 1;
            var echelle = toile.AddComponent<CanvasScaler>(); echelle.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize; echelle.referenceResolution = RESOLUTION_REFERENCE;
            toile.AddComponent<GraphicRaycaster>();
            var fond = Bloc("Horloge", toile.transform, FOND);
            var cadre = (RectTransform)fond.transform; cadre.anchorMin = cadre.anchorMax = cadre.pivot = Vector2.one; cadre.anchoredPosition = new Vector2(-MARGE, -MARGE);
            var pile = fond.AddComponent<VerticalLayoutGroup>(); pile.padding = new RectOffset(RETRAIT, RETRAIT, RETRAIT, RETRAIT); pile.spacing = RETRAIT;
            pile.childControlWidth = pile.childControlHeight = true; pile.childForceExpandWidth = pile.childForceExpandHeight = false;
            var ajuste = fond.AddComponent<ContentSizeFitter>(); ajuste.horizontalFit = ajuste.verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            texte = Ecrire("Date", fond.transform, "");
            var rang = new GameObject("Commandes", typeof(RectTransform)); rang.transform.SetParent(fond.transform, false);
            var ligne = rang.AddComponent<HorizontalLayoutGroup>(); ligne.spacing = RETRAIT; ligne.childControlWidth = ligne.childControlHeight = true; ligne.childForceExpandWidth = false;
            Bouton(rang.transform, "Moins vite", Ralentir);
            libellePause = Bouton(rang.transform, "Pause", Basculer);
            Bouton(rang.transform, "Plus vite", Accelerer);
        }

        private static GameObject Bloc(string nom, Transform parent, Color couleur) {
            var objet = new GameObject(nom, typeof(RectTransform)); objet.transform.SetParent(parent, false);
            objet.AddComponent<Image>().color = couleur; return objet;
        }

        private static Text Ecrire(string nom, Transform parent, string message) {
            var t = new GameObject(nom, typeof(RectTransform)).AddComponent<Text>(); t.transform.SetParent(parent, false);
            t.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf"); t.fontSize = TAILLE_POLICE; t.color = Color.white; t.raycastTarget = false;
            t.horizontalOverflow = HorizontalWrapMode.Overflow; t.verticalOverflow = VerticalWrapMode.Overflow; t.text = message; return t;
        }

        private static Text Bouton(Transform parent, string libelle, UnityEngine.Events.UnityAction action) {
            var objet = Bloc("Bouton " + libelle, parent, BOUTON);
            var marge = objet.AddComponent<HorizontalLayoutGroup>(); marge.padding = new RectOffset(RETRAIT, RETRAIT, RETRAIT / 2, RETRAIT / 2);
            marge.childControlWidth = marge.childControlHeight = true;
            objet.AddComponent<Button>().onClick.AddListener(action);
            return Ecrire("Libellé", objet.transform, libelle);
        }

        private static void Detruire(UnityEngine.Object o) { if (Application.isPlaying) Destroy(o); else DestroyImmediate(o); }
    }
}
