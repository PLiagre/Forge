using System;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Forge.Pont {
    // De la carte à la capitale. Le composant relit l'aiguillage toutes les `PERIODE_LECTURE_S` pour connaître le siège et
    // la scène de la ville du joueur ; il ne descend jamais de lui-même. La ville s'ouvre par `Entrer` (le bouton « Entrer
    // dans la ville » du cabinet) ou par un double-clic sur le siège lu, une seule fois ; ensuite plus rien ne se lit.
    // Une absence ne change ni le siège ni la scène lus. Par défaut, la scène se charge par le fondu de TransitionDeVue.
    [DefaultExecutionOrder(10)] // après CarteDessinee, dont il prend la caméra créée
    public sealed class PassageALaCapitale : MonoBehaviour {
        public const float PERIODE_LECTURE_S = 1;
        private static readonly TimeSpan DELAI = TimeSpan.FromSeconds(5);

        public int port = PanneauLieu.DEFAULT_SERVICE_PORT;
        public new Camera camera; // vide : celle de la CarteDessinee du même objet
        public Action<string> ChargerScene { get; set; } // vide : TransitionDeVue.Lancer vers la ville, avec le port du passage

        private Task<Lecture<CapitaleAOuvrir>> enCours; private double prochaineLecture; private bool demarre;

        public bool RequeteEnVol => enCours != null && !enCours.IsCompleted;
        public string Absence { get; private set; } // la cause de la dernière lecture manquée ; null après une lecture servie
        public string SceneDemandee { get; private set; } // null tant que rien n'est chargé
        // La cellule du siège de la dernière lecture servie qui rend `Ville` ; nulle après `Depart` ou `PasDeKit`.
        public long? SiegeLu { get; private set; }
        public const double DELAI_DOUBLE_CLIC_S = 0.5;
        private string villeLue; private long? premierClic; private double instantDuClic;

        // Le second de deux clics sur la même cellule, à `DELAI_DOUBLE_CLIC_S` au plus, descend s'il tombe sur le
        // siège lu et que rien n'est demandé. Le clic qui ferme un double-clic n'en ouvre pas un autre.
        public bool Cliquer(long? cellule, double maintenant) {
            bool double_ = cellule != null && cellule == premierClic && maintenant - instantDuClic <= DELAI_DOUBLE_CLIC_S;
            premierClic = double_ ? null : cellule; instantDuClic = maintenant;
            if (!double_ || cellule != SiegeLu || SceneDemandee != null) return false;
            Descendre(villeLue, cellule); return true;
        }

        // La ville servie au joueur : sa scène et la cellule de son siège, telles que le service les dit. Une seule descente.
        public bool Entrer(string scene, long cellule) {
            if (string.IsNullOrEmpty(scene) || SceneDemandee != null) return false;
            Descendre(scene, cellule); return true;
        }

        private void Start() { var carte = GetComponent<CarteDessinee>(); Demarrer(camera != null ? camera : carte != null ? carte.camera : null); }
        private void Update() => Pas(Time.realtimeSinceStartupAsDouble);
        private void OnDestroy() => Arreter();

        public void Demarrer(Camera vue) {
            camera = vue;
            if (camera == null) { Debug.LogError("PassageALaCapitale : pas de caméra, le passage ne lit rien", this); return; }
            demarre = true;
        }

        public void Arreter() { enCours = null; demarre = false; }

        public void Pas(double maintenant) {
            if (!demarre || SceneDemandee != null) return;
            if (enCours != null && enCours.IsCompleted) { var fini = enCours; enCours = null; Appliquer(fini); }
            if (enCours != null || SceneDemandee != null || maintenant < prochaineLecture) return;
            prochaineLecture = maintenant + PERIODE_LECTURE_S;
            int p = port; enCours = Task.Run(() => AiguillageDeCapitale.Lire(p, DELAI));
        }

        private void Appliquer(Task<Lecture<CapitaleAOuvrir>> fini) {
            if (fini.IsFaulted) { Absence = "passage : " + fini.Exception.GetBaseException().Message; return; }
            var lecture = fini.Result;
            if (!lecture.Presente) { Absence = lecture.Absence; return; }
            Absence = null;
            bool ville = lecture.Donnees.Destination == DestinationDeCapitale.Ville;
            SiegeLu = ville ? lecture.Donnees.Cellule : null; villeLue = ville ? lecture.Donnees.Scene : null;
        }

        // La remise, puis le chargement : celui qu'on a donné, sinon le fondu au noir vers la vue de la ville.
        private void Descendre(string scene, long? cellule) {
            SceneDemandee = scene; (sceneRemise, celluleRemise) = (scene, cellule); enCours = null;
            if (ChargerScene != null) ChargerScene(scene); else TransitionDeVue.Lancer(scene, VueDuJeu.Ville, port);
        }

        // La cellule du siège, retenue juste avant le chargement pour la seule scène demandée. Une prise l'efface, que la
        // scène corresponde ou non : une seule ville en profite.
        private static string sceneRemise; private static long? celluleRemise;
        public static long? PrendreCelluleRemise(string scene)
        {
            long? cellule = scene == sceneRemise ? celluleRemise : null;
            (sceneRemise, celluleRemise) = (null, null);
            return cellule;
        }

        // À l'ouverture de la carte, le passage manquant se pose sur chaque CarteDessinee, avec son port.
        // Un second avis ne crée rien. Une autre scène n'est pas touchée. Le Start prend ensuite la caméra.
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Installer() {
            SceneManager.sceneLoaded -= AuChargement; SceneManager.sceneLoaded += AuChargement;
            AuChargement(SceneManager.GetActiveScene(), LoadSceneMode.Single);
        }

        public static void AuChargement(Scene scene, LoadSceneMode mode) {
            if (!scene.IsValid() || scene.name != OuvertureDeLaCarte.SCENE) return;
            foreach (CarteDessinee carte in UnityEngine.Object.FindObjectsByType<CarteDessinee>(FindObjectsSortMode.None)) {
                if (carte.gameObject.scene != scene) continue;
                if (carte.GetComponent<ReperesDeDepart.NomDuSiege>() == null) carte.gameObject.AddComponent<ReperesDeDepart.NomDuSiege>(); // le nom du siège, que le cabinet n'arrête pas
                if (carte.GetComponent<PassageALaCapitale>() == null) carte.gameObject.AddComponent<PassageALaCapitale>().port = carte.port;
            }
        }
    }
}
