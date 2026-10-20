using System;
using System.Collections.Generic;
using System.Globalization;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace Forge.Pont {
    public enum VueDuJeu { Ville, Carte }

    // Lot #728 : la vitesse du monde dans chaque vue, en jours par seconde, lue dans `Resources/ReglagesDesVues.json`, que
    // le lanceur Python lit aussi. Aucune valeur de repli : un réglage absent, faux ou nul lève en nommant sa clé.
    public sealed class ReglagesDesVues {
        public const string RESSOURCE = "ReglagesDesVues";
        public double VitesseVille { get; } public double VitesseCarte { get; }
        private ReglagesDesVues(double ville, double carte) { VitesseVille = ville; VitesseCarte = carte; }
        public double Vitesse(VueDuJeu vue) => vue == VueDuJeu.Ville ? VitesseVille : VitesseCarte;
        public static ReglagesDesVues Lire(string json) { var r = LecteurJson.LireObjet(json); return new ReglagesDesVues(Positive(r, "VITESSE_VILLE"), Positive(r, "VITESSE_CARTE")); }
        public static ReglagesDesVues Charger() { var t = Resources.Load<TextAsset>(RESSOURCE); return t != null ? Lire(t.text) : throw new InvalidOperationException("ressource " + RESSOURCE + " absente de Resources"); }
        // Une vitesse de vue nulle mettrait le monde en pause en changeant de vue : refusée, comme une négative ou non finie.
        private static double Positive(Dictionary<string, object> racine, string cle) {
            if (!racine.TryGetValue(cle, out object brute)) throw new FormatException("réglage " + cle + " absent");
            if (brute is double v && v > 0 && !double.IsInfinity(v)) return v;
            throw new FormatException("réglage " + cle + " : un nombre fini > 0 attendu, reçu " + (brute is string s ? "le texte \"" + s + "\"" : Convert.ToString(brute, CultureInfo.InvariantCulture)));
        }
    }

    // Lot #728 : le passage d'une vue à l'autre. Le noir monte en `DUREE_FONDU_S`, la scène se charge une seule fois, et le
    // noir redescend sans attendre le service. Après le chargement seulement, une requête hors du fil principal lit
    // `/horloge` ; si le monde avance, elle lui donne la vitesse de la vue d'arrivée. Un monde en pause y reste ; une absence
    // n'arrête ni le passage ni l'image. Le service tient seul le temps : rien ici ne le lance ni ne compte à sa place.
    public sealed class TransitionDeVue : MonoBehaviour {
        public const double DUREE_FONDU_S = 0.4;
        private static readonly TimeSpan DELAI = TimeSpan.FromSeconds(2); private static TransitionDeVue lancee;
        public int port = PanneauLieu.DEFAULT_SERVICE_PORT;
        public Action<string> ChargerScene { get; set; } = nom => SceneManager.LoadScene(nom);
        private double? debut, charge; private string scene; private double vitesse;
        private Task<(double? posee, string absence)> enCours; private GameObject toile; private Image noir;
        public float Opacite { get; private set; } public bool EnCours => debut != null;
        public bool RequeteEnVol => enCours != null && !enCours.IsCompleted;
        public string SceneChargee { get; private set; } // null avant le chargement
        public double? VitessePosee { get; private set; } // la vitesse que le service rend au POST ; null sans POST
        public string Absence { get; private set; } // la cause d'une horloge manquée ; null si elle est lue (même en pause)
        private void Update() { Pas(Time.realtimeSinceStartupAsDouble); if (SceneChargee != null && !EnCours) Destroy(gameObject); }
        private void OnDestroy() => Arreter();
        public static TransitionDeVue Lancer(string scene, VueDuJeu vue, int port) {
            if (lancee != null && lancee.EnCours) return null;
            var objet = new GameObject("Transition de vue"); if (Application.isPlaying) DontDestroyOnLoad(objet);
            lancee = objet.AddComponent<TransitionDeVue>(); lancee.port = port;
            try { lancee.Commencer(scene, vue, Time.realtimeSinceStartupAsDouble); } catch { if (Application.isPlaying) Destroy(objet); else DestroyImmediate(objet); throw; } return lancee;
        }
        public bool Commencer(string scene, VueDuJeu vue, double maintenant) {
            if (EnCours) return false; vitesse = ReglagesDesVues.Charger().Vitesse(vue);
            (this.scene, debut, charge, SceneChargee, VitessePosee, Absence, Opacite) = (scene, maintenant, null, null, null, null, 0);
            if (toile == null) Construire(); Montrer(); return true;
        }
        public void Arreter() { enCours = null; debut = null; Opacite = 0; if (toile != null) toile.SetActive(false); }
        public void Pas(double maintenant) {
            if (debut == null) return; if (enCours != null && enCours.IsCompleted) { var fini = enCours; enCours = null; Appliquer(fini); }
            if (charge == null) {
                Opacite = Mathf.Clamp01((float)((maintenant - debut.Value) / DUREE_FONDU_S));
                if (Opacite >= 1) { charge = maintenant; SceneChargee = scene; ChargerScene(scene); Regler(); }
            } else Opacite = 1 - Mathf.Clamp01((float)((maintenant - charge.Value) / DUREE_FONDU_S));
            if (charge != null && Opacite <= 0 && enCours == null) debut = null;
            Montrer();
        }
        // Lit l'horloge, et ne pose la vitesse que si le monde avance. Un client de 2 s par transition, disposé.
        private void Regler() {
            int p = port; double v = vitesse;
            enCours = Task.Run<(double? posee, string absence)>(() => { using (var client = new ClientHorloge(p, DELAI)) {
                var lue = client.Lire(); if (!lue.Presente) return (null, lue.Absence); if (lue.Donnees.JoursParSeconde <= 0) return (null, null);
                var reglee = client.Regler(v); if (!reglee.Presente) return (null, reglee.Absence);
                return (reglee.Donnees.JoursParSeconde, null);
            } });
        }
        private void Appliquer(Task<(double? posee, string absence)> fini) { if (fini.IsFaulted) Absence = "horloge : " + fini.Exception.GetBaseException().Message; else (VitessePosee, Absence) = fini.Result; }
        private void Montrer() { noir.color = new Color(0, 0, 0, Opacite); toile.SetActive(EnCours); }
        // Une toile au-dessus de toutes les autres ; l'image noire plein écran prend les clics pendant le passage.
        private void Construire() {
            toile = new GameObject("Toile de la transition", typeof(RectTransform)); toile.transform.SetParent(transform, false);
            var canvas = toile.AddComponent<Canvas>(); canvas.renderMode = RenderMode.ScreenSpaceOverlay; canvas.sortingOrder = short.MaxValue; toile.AddComponent<GraphicRaycaster>();
            noir = new GameObject("Noir", typeof(RectTransform)).AddComponent<Image>(); noir.transform.SetParent(toile.transform, false); noir.raycastTarget = true;
            var zone = noir.rectTransform; zone.anchorMin = Vector2.zero; zone.anchorMax = Vector2.one; zone.offsetMin = zone.offsetMax = Vector2.zero;
        }
    }
}
