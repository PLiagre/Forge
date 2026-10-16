using System.Linq;
using Forge.Pont;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace Forge.Interface
{
    [DefaultExecutionOrder(100)]
    public sealed class CabinetDeCarte : MonoBehaviour
    {
        public LecturePartie Partie { get; set; }
        CarteDessinee carte;
        HorlogeDeCarte horloge;
        FicheDeCellule fiche;
        GameObject toile;
        Text date, maison, territoire, apercu, aide;
        Transform choix;
        Button confirmer;
        Button[] temps;
        CelluleDeCarte retenue;
        MeshRenderer territoireTeinte;
        FicheDeDepart candidate;
        string liste;
        double prochaineLecture;

        void Start() => Construire();
        void Update()
        {
            if (toile == null) return;
            if (!Partie.Occupee && Time.realtimeSinceStartupAsDouble >= prochaineLecture)
            {
                prochaineLecture = Time.realtimeSinceStartupAsDouble + 1;
                _ = Partie.Actualiser();
            }
            if (Mouse.current?.rightButton.wasPressedThisFrame == true
                && carte.camera != null && carte.camera.pixelRect.Contains(Mouse.current.position.ReadValue())
                && EventSystem.current?.IsPointerOverGameObject() != true) Garder(fiche.Survolee);
            Afficher();
        }

        public void Construire()
        {
            if (toile != null) return;
            carte = GetComponent<CarteDessinee>(); horloge = GetComponent<HorlogeDeCarte>(); fiche = GetComponent<FicheDeCellule>();
            var prototype = GetComponent<ReperesDeDepart>();
            if (prototype != null) { prototype.enabled = false; prototype.Arreter(); }
            Partie = Partie ?? LecturePartie.Locale(carte.port);
            foreach (var ancien in GetComponentsInChildren<Canvas>()) ancien.gameObject.SetActive(false);
            if (carte.camera != null) carte.camera.rect = new Rect(0, 0, .67f, 1);
            toile = new GameObject("Cabinet", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            toile.transform.SetParent(transform, false);
            toile.GetComponent<Canvas>().renderMode = RenderMode.ScreenSpaceOverlay;
            toile.GetComponent<Canvas>().sortingOrder = 10;
            var echelle = toile.GetComponent<CanvasScaler>();
            echelle.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            echelle.referenceResolution = new Vector2(1920, 1080);
            var fond = new GameObject("Fond des dossiers", typeof(RectTransform), typeof(Image)).GetComponent<RectTransform>();
            fond.SetParent(toile.transform, false);
            fond.anchorMin = new Vector2(.67f, 0); fond.anchorMax = Vector2.one;
            fond.offsetMin = fond.offsetMax = Vector2.zero;
            fond.GetComponent<Image>().color = SocleInterface.Couleur("fond");
            var bandeau = SocleInterface.Panneau(toile.transform, "FORGE · Le cabinet", 0, 0, 1920, 100);
            date = SocleInterface.Texte(bandeau, "Lecture de la date…", 480, 24, 760);
            temps = new[] { Bouton(bandeau, "Ralentir", 1296, 20, 180, horloge.Ralentir),
                Bouton(bandeau, "Pause / Reprendre", 1496, 20, 200, horloge.Basculer),
                Bouton(bandeau, "Accélérer", 1716, 20, 180, horloge.Accelerer) };
            var dossier = SocleInterface.Panneau(toile.transform, "Votre maison", 1312, 124, 584, 536);
            maison = SocleInterface.Texte(dossier, "Lecture de la partie…", 24, 88, 536);
            choix = new GameObject("Maisons proposées", typeof(RectTransform)).transform;
            choix.SetParent(dossier, false);
            var rect = (RectTransform)choix;
            rect.anchorMin = rect.anchorMax = rect.pivot = new Vector2(0, 1);
            apercu = SocleInterface.Texte(dossier, "Consultez une maison avant de vous engager.", 24, 336, 536);
            apercu.rectTransform.sizeDelta = new Vector2(536, 100);
            confirmer = Bouton(dossier, "Choisir cette maison", 24, 468, 536,
                () => { if (candidate != null) _ = Partie.Choisir(candidate.Id); });
            var couleurs = confirmer.colors; couleurs.normalColor = SocleInterface.Couleur("alerte"); confirmer.colors = couleurs;
            var lieu = SocleInterface.Panneau(toile.transform, "Territoire conservé", 1312, 684, 584, 372);
            territoire = SocleInterface.Texte(lieu, "Clic droit sur une terre pour garder son dossier ouvert.", 24, 88, 536);
            territoire.rectTransform.sizeDelta = new Vector2(536, 260);
            var guide = SocleInterface.Panneau(toile.transform, "Parcourir le monde", 24, 924, 1238, 132);
            aide = SocleInterface.Texte(guide, "Glisser : déplacer · Molette : zoomer · Clic droit : conserver un territoire", 24, 88, 1190);
            foreach (var texte in toile.GetComponentsInChildren<Text>()) texte.supportRichText = false;
            Afficher();
        }

        static Button Bouton(Transform parent, string nom, float x, float y, float largeur, UnityEngine.Events.UnityAction action)
        {
            var bouton = SocleInterface.Commande(parent, nom, x, y, () => action());
            bouton.GetComponent<RectTransform>().sizeDelta = new Vector2(largeur, SocleInterface.HauteurCommande);
            bouton.GetComponentInChildren<Text>().rectTransform.sizeDelta = new Vector2(largeur, SocleInterface.HauteurCommande);
            bouton.GetComponentInChildren<Text>().supportRichText = false;
            return bouton;
        }

        public void Garder(CelluleDeCarte cellule)
        {
            if (cellule == null) return;
            retenue = cellule;
            if (territoireTeinte != null) territoireTeinte.SetPropertyBlock(null);
            territoireTeinte = GetComponentsInChildren<MeshRenderer>().FirstOrDefault(r => r.name == "Cellule " + cellule.CellId);
            if (territoireTeinte == null) return;
            var teinte = new MaterialPropertyBlock();
            teinte.SetColor("_BaseColor", SocleInterface.Couleur("alerte"));
            territoireTeinte.SetPropertyBlock(teinte);
        }

        public void Afficher()
        {
            date.text = horloge.Absence != null ? "Date indisponible : le monde ne répond pas"
                : horloge.Lue != null ? HorlogeDeCarte.Decrire(horloge.Lue) : "Date en attente du monde";
            foreach (var bouton in temps) bouton.interactable = horloge.Lue != null && horloge.Absence == null;
            temps[1].GetComponentInChildren<Text>().text = horloge.Lue?.JoursParSeconde == 0 ? "Reprendre" : "Pause";
            if (carte.CellulesServies < 0) aide.text = carte.TexteAffiche ?? "La carte se prépare…";
            else aide.text = "Glisser : déplacer · Molette : zoomer · Clic droit : conserver un territoire";
            if (retenue != null)
            {
                var monde = Partie.Monde;
                territoire.text = FicheDeCellule.Decrire(retenue, monde == null ? null : monde.Presente
                    ? Lecture<MondeLu>.De(monde.Donnees.Monde) : Lecture<MondeLu>.Absent(monde.Absence));
            }
            AfficherMaison();
        }

        void AfficherMaison()
        {
            var monde = Partie.Monde;
            bool proposer = monde != null && monde.Presente && monde.Donnees.MaisonDuJoueur == null;
            choix.gameObject.SetActive(proposer);
            confirmer.gameObject.SetActive(proposer);
            confirmer.interactable = candidate != null && Partie.PeutChoisir;
            apercu.gameObject.SetActive(proposer);
            if (monde == null) return;
            if (!monde.Presente) { EtatsLecture.Afficher(maison, EtatLecture.Panne, monde.Absence); return; }
            maison.color = SocleInterface.Couleur("encre");
            maison.rectTransform.sizeDelta = new Vector2(536, 80);
            if (!proposer)
            {
                var lue = Partie.Maison;
                if (lue == null || !lue.Presente) { EtatsLecture.Afficher(maison, EtatLecture.Absence, lue?.Absence ?? "Maison en attente"); return; }
                maison.text = (lue.Donnees.Nom ?? lue.Donnees.Absents["nom"]) + "\nSiège : " + lue.Donnees.Siege.Nom
                    + "\n" + lue.Donnees.Lieux.Count + " lieux tenus · relevé au tick " + monde.Donnees.Monde.Tick;
                maison.rectTransform.sizeDelta = new Vector2(536, 180);
                maison.color = SocleInterface.Couleur("encre");
                return;
            }
            maison.text = "Choisissez votre maison.\nLe choix sera appliqué par le monde.";
            var departs = Partie.Departs;
            if (departs == null || !departs.Presente) { EtatsLecture.Afficher(maison, EtatLecture.Absence, departs?.Absence ?? "Départs en attente"); return; }
            string cle = string.Join("\n", departs.Donnees.Fiches.Select(f => f.Id + " " + f.Maison));
            if (cle != liste)
            {
                foreach (Transform ancien in choix) Destroy(ancien.gameObject);
                liste = cle; candidate = null;
                int i = 0;
                foreach (var f in departs.Donnees.Fiches)
                {
                    Bouton(choix, f.Maison, 24 + i % 2 * 276, 168 + i / 2 * 52, 260, () => candidate = f);
                    i++;
                }
            }
            foreach (var bouton in choix.GetComponentsInChildren<Button>()) bouton.interactable = Partie.PeutChoisir;
            if (candidate != null) apercu.text = candidate.Nom + " · " + candidate.Siege.Nom
                + "\n" + candidate.Habitants + " habitants dans la cellule du siège"
                + "\nSuzerain : " + (candidate.Suzerain?.Nom ?? "aucun");
            var recu = Partie.Recu;
            if (recu != null) apercu.text = recu.Acceptee ? "Choix reçu au tick " + recu.AppliqueeAuTick + ".\nReprenez le temps pour son application au prochain tick."
                : recu.Presente ? "Demande refusée : " + recu.Erreur : "Envoi non confirmé : " + recu.Absence;
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Installer()
        {
            SceneManager.sceneLoaded -= Ouvrir;
            SceneManager.sceneLoaded += Ouvrir;
            Ouvrir(SceneManager.GetActiveScene(), LoadSceneMode.Single);
        }
        static void Ouvrir(Scene scene, LoadSceneMode mode)
        {
            if (scene.name != OuvertureDeLaCarte.SCENE) return;
            foreach (var carte in FindObjectsByType<CarteDessinee>(FindObjectsSortMode.None))
                if (carte.gameObject.scene == scene && carte.GetComponent<CabinetDeCarte>() == null) carte.gameObject.AddComponent<CabinetDeCarte>();
        }
#if UNITY_EDITOR
        [UnityEditor.MenuItem("Forge/Interface/Jouer sur la carte")]
        public static void Jouer()
        {
            if (!UnityEditor.SceneManagement.EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            UnityEditor.SceneManagement.EditorSceneManager.OpenScene("Assets/ForgeLocal3D/Carte/Forge_Carte.unity");
            UnityEditor.EditorApplication.isPlaying = true;
        }
#endif
    }
}
