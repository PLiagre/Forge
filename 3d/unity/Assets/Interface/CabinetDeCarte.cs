using System.Collections.Generic;
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
        public const float SEUIL_CLIC_PX = 6f;
        public const string DOSSIERS = "Dossiers de la barre";
        public const string AIDE ="Clic : choisir une terre · Glisser : déplacer · Molette : zoomer · Échap : fermer";
        public const string PAYS = "Pays de la barre";
        public const string ETAT = "État de la carte";
        // La ligne du prochain geste (à droite de la barre) et la surbrillance des terres de départ.
        public const string GUIDE = "Prochain geste";
        // Elle nomme des boutons, jamais une touche.
        public const string CHOISIR = "Choisissez votre pays, puis « Commencer »";
        public const string CHOIX_RECU = "Choix reçu : « Reprendre » lance le temps, le monde l'applique au jour suivant";
        public const string LANCER = "« Reprendre » lance le temps du monde";
        public const string ENTRER = " · « Entrer dans la ville » ouvre votre capitale";
        const string INVITATION = "Clic gauche sur une terre pour ouvrir son dossier.";
        public LecturePartie Partie { get; set; }
        public CelluleDeCarte Retenue => retenue;
        public AccueilDuPays Accueil => accueil;
        public BoutonDeLaVille Ville => ville;
        // La demi-hauteur, en km, de la vue posée sur le siège du joueur quand sa maison apparaît : sa terre et ses voisines.
        public const float DEMI_SUR_LE_SIEGE_KM = 220f;
        CarteDessinee carte;
        HorlogeDeCarte horloge;
        FicheDeCellule fiche;
        GameObject toile;
        Text date, barre, guide, maison, territoire, etat;
        RectTransform dossier, lieu;
        AccueilDuPays accueil;
        BoutonDeLaVille ville;
        string centreSur; // la maison sur le siège de laquelle la vue s'est posée, une fois
        BarreDuPays jauges;
        readonly HashSet<long> terresEclairees = new HashSet<long>(); // les terres de départ que la carte dessine
        string ensembleDesTerres;
        Button[] temps;
        CelluleDeCarte retenue;
        double prochaineLecture;
        Vector2? depart; bool eloigne;

        void Start() => Construire();
        void Update()
        {
            if (toile == null) return;
            if (!Partie.Occupee && Time.realtimeSinceStartupAsDouble >= prochaineLecture)
            {
                prochaineLecture = Time.realtimeSinceStartupAsDouble + 1;
                _ = Partie.Actualiser();
            }
            var souris = Mouse.current; Vector2 ici = souris?.position.ReadValue() ?? Vector2.zero;
            bool appui = souris?.leftButton.wasPressedThisFrame == true, relache = souris?.leftButton.wasReleasedThisFrame == true, hors = (appui || relache) && HorsCarte(ici);
            if (relache && !hors) fiche.Survoler(ici);
            Noter(ici, appui, relache, hors, relache && !hors ? fiche.Survolee : null);
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
            MatieresCabinet.Habiller(fond.GetComponent<Image>(), true);
            var bandeau = SocleInterface.Panneau(toile.transform, "FORGE · Le cabinet", 0, 0, 1920, 124, true); // 124, le haut de chaque panneau posé dessous
            // Les icônes des dossiers, entre la date et les commandes du temps ; le bandeau garde ses trois boutons enfants directs.
            var dossiers = new GameObject(DOSSIERS, typeof(RectTransform)).GetComponent<RectTransform>(); dossiers.SetParent(bandeau, false);
            dossiers.anchorMin = dossiers.anchorMax = dossiers.pivot = new Vector2(0, 1);
            dossiers.anchoredPosition = new Vector2(1112, -20); dossiers.sizeDelta = new Vector2(136, 44);
            // L'icône du pays, hors des dossiers, entre le titre du bandeau et la date posée en x 480.
            var pays = new GameObject(PAYS, typeof(RectTransform)).GetComponent<RectTransform>(); pays.SetParent(bandeau, false);
            pays.anchorMin = pays.anchorMax = pays.pivot = new Vector2(0, 1);
            pays.anchoredPosition = new Vector2(408, -20); pays.sizeDelta = new Vector2(56, 44);
            date = SocleInterface.Texte(bandeau, "Lecture de la date…", 480, 24, 400); // x 480 à 880, avant « Entrer dans la ville »
            date.color = SocleInterface.Couleur("papier");
            barre = SocleInterface.Texte(bandeau, "Lecture de la maison…", 24, 72, 1872); // sous le filet, dans les 100 px du bandeau
            barre.color = SocleInterface.Couleur("papier"); barre.rectTransform.sizeDelta = new Vector2(1872, 26);
            // À droite des comptes, au-dessus des jauges, sous les commandes du temps : x 1104 à 1896, y 72 à 98.
            guide = SocleInterface.Texte(bandeau, "", 1104, 72, 792); guide.name = GUIDE;
            guide.rectTransform.sizeDelta = new Vector2(792, 26); guide.alignment = TextAnchor.MiddleRight; guide.color = SocleInterface.Couleur("papier"); guide.raycastTarget = false;
            jauges = new BarreDuPays(bandeau); // sous la barre des comptes, les trois jauges et les trois réserves de points
            ville = new BoutonDeLaVille(bandeau, () => Partie, BoutonDeLaVille.Par(gameObject)); // entre la date et les dossiers
            temps = new[] { Bouton(bandeau, "Ralentir", 1296, 20, 180, horloge.Ralentir, "Passe le temps du monde à la vitesse inférieure."),
                Bouton(bandeau, "Pause / Reprendre", 1496, 20, 200, horloge.Basculer, "Arrête le temps du monde, ou le relance à la vitesse choisie."),
                Bouton(bandeau, "Accélérer", 1716, 20, 180, horloge.Accelerer, "Passe le temps du monde à la vitesse supérieure.") };
            dossier = SocleInterface.Panneau(toile.transform, "Votre maison", 1312, 124, 584, 536);
            maison = SocleInterface.Texte(dossier, "Lecture de la partie…", 24, 88, 536);
            gameObject.AddComponent<CommandesMaison>().Initialiser(dossier,
                () => Partie.Monde?.Presente == true ? Partie.Monde.Donnees.MaisonDuJoueur : null,
                LectureDossier.Locale(carte.port), OrdreConfirme.Local(carte.port));
            lieu = SocleInterface.Panneau(toile.transform, "Territoire conservé", 1312, 684, 584, 372);
            territoire = SocleInterface.Texte(lieu, INVITATION, 24, 88, 536);
            territoire.rectTransform.sizeDelta = new Vector2(536, 260);
            gameObject.AddComponent<DossierTerritoire>().Initialiser(territoire, carte.port, () => retenue);
            gameObject.AddComponent<DossierBourg>().Initialiser(toile.transform, lieu, carte.port, () => retenue);
            // Plus de panneau en bas de la carte ; l'état de la carte s'écrit au centre de sa vue (0,67 × 1920 / 2, 540).
            etat = SocleInterface.Texte(toile.transform, "La carte se prépare…", 343, 492, 600); etat.name = ETAT;
            etat.rectTransform.sizeDelta = new Vector2(600, 96); etat.alignment = TextAnchor.MiddleCenter; etat.color = SocleInterface.Couleur("papier"); etat.raycastTarget = false;
            gameObject.AddComponent<CalquesCarte>().Initialiser(carte, toile.transform,
                () => Partie.Monde?.Presente == true ? Partie.Monde.Donnees.Monde : null, () => retenue);
            var menu = gameObject.AddComponent<MenuCabinet>(); menu.Initialiser(toile.transform); menu.AvantDOuvrir = Relacher;
            // Le Menu cède la colonne de l'icône du pays (x 408) : il passe de 330 à 280, entre les glyphes du titre et l'icône, sans la recouvrir.
            ((RectTransform)toile.transform.Find("Menu")).anchoredPosition = new Vector2(280, -20);
            var bulle = toile.transform.Find("Menu").GetComponent<Infobulle>(); bulle.phrase = bulle.Phrase + "\n" + AIDE; // les gestes de la carte, au survol du Menu
            gameObject.AddComponent<DossierVoisins>().Initialiser(toile.transform, dossiers, carte.port);
            foreach (var texte in toile.GetComponentsInChildren<Text>()) texte.supportRichText = false;
            gameObject.AddComponent<DossierMaison>().Initialiser(toile.transform,
                () => Partie.Monde?.Presente == true ? Partie.Monde.Donnees.MaisonDuJoueur : null, carte.port, dossiers);
            var dossierPays = gameObject.AddComponent<DossierPays>();
            dossierPays.Initialiser(toile.transform, pays, () => Partie.Monde, () => Partie.Terres, LectureDossier.Locale(carte.port), NomsDesTerres.Local(carte.port));
            // À droite du feuillet du pays, ses gestes ; le panneau s'ouvre et se ferme avec lui.
            gameObject.AddComponent<GestesDesJauges>().Initialiser(dossierPays.Cadre, () => Partie.Monde, () => Partie.Gestes, OrdreConfirme.Local(carte.port));
            // Le feuillet de la guerre, ouvert depuis le panneau « Votre maison » ; ses ordres visent la terre gardée sur la carte.
            gameObject.AddComponent<DossierGuerre>().Initialiser(toile.transform, dossier, () => Partie.Monde?.Presente == true ? Partie.Monde.Donnees.MaisonDuJoueur : null,
                () => retenue, OrdreConfirme.Local(carte.port), NomsDesTerres.Local(carte.port), carte.port);
            gameObject.AddComponent<VillesDeCarte>().Installer();
            var lieux = gameObject.AddComponent<LieuxDeCarte>(); lieux.Installer();
            var fleches = gameObject.AddComponent<FlechesDeCarte>(); fleches.Installer(lieux);
            var guerre = gameObject.AddComponent<CarteDeLaGuerre>(); guerre.Installer(); var calques = GetComponent<CalquesCarte>(); calques.Brancher(lieux, fleches, guerre); lieux.Eviter(guerre, calques);
            // L'accueil prend la colonne des deux panneaux tant qu'aucune maison n'est servie ; il lit le pays des terres sur la carte de la guerre.
            int port = carte.port;
            accueil = new AccueilDuPays(toile.transform, () => Partie, () => guerre.Terres,
                id => { using (var c = new ClientPays(port, System.TimeSpan.FromSeconds(10))) return c.LireTerres(id); },
                () => horloge.Lue != null && horloge.Lue.JoursParSeconde == 0, horloge.Basculer);
            foreach (var texte in accueil.Panneau.GetComponentsInChildren<Text>(true)) texte.supportRichText = false;
            gameObject.AddComponent<InfobulleDeTerre>().Initialiser(toile.GetComponent<Canvas>(), LectureDossier.Locale(carte.port), () => fiche.Survolee, LectureDossier.Locale(carte.port)); // la seconde lecture, sur /modificateurs
            Afficher();
        }

        void OnDestroy() => ViderTerres();

        static Button Bouton(Transform parent, string nom, float x, float y, float largeur, UnityEngine.Events.UnityAction action, string phrase)
        {
            var bouton = SocleInterface.Commande(parent, nom, x, y, () => action(), phrase: phrase);
            bouton.GetComponent<RectTransform>().sizeDelta = new Vector2(largeur, SocleInterface.HauteurCommande);
            bouton.GetComponentInChildren<Text>().rectTransform.sizeDelta = new Vector2(largeur, SocleInterface.HauteurCommande);
            bouton.GetComponentInChildren<Text>().supportRichText = false;
            return bouton;
        }

        // Les commandes de la toile, cachées comprises, qui ne disent pas ce qu'elles font ; une phrase qui répète le nom ne dit rien.
        public static string[] CommandesSansPhrase(Transform toile)
        {
            var boutons = toile.GetComponentsInChildren<Button>(true);
            if (boutons.Length == 0) throw new System.ArgumentException("aucune commande dans le cabinet");
            return boutons.Where(b => { var i = b.GetComponent<Infobulle>(); return i == null || string.IsNullOrWhiteSpace(i.Phrase) || i.Phrase == b.name; }) // == d'Unity : pas de « is », qui voit le faux null de l'éditeur
                .Select(b => b.name).ToArray();
        }

        // Un clic gauche court garde la terre ; s'écarter de plus de SEUIL_CLIC_PX (celui du survol, pour que ce clic compte aussi au double-clic) en fait un glisser.
        public bool Noter(Vector2 ici, bool appui, bool relache, bool horsCarte, CelluleDeCarte sous)
        {
            if (appui) { depart = horsCarte ? (Vector2?)null : ici; eloigne = false; }
            if (depart is Vector2 d && (ici - d).magnitude > SEUIL_CLIC_PX) eloigne = true;
            bool clic = relache && depart != null && !eloigne && !horsCarte && sous != null;
            if (relache) depart = null;
            if (clic) Garder(sous);
            return clic;
        }
        public bool HorsCarte(Vector2 ecran) // hors de la vue de la carte, ou sur un graphique de l'interface, au point donné
        {
            if (carte.camera == null || !carte.camera.pixelRect.Contains(ecran)) return true;
            var touches = new List<RaycastResult>();
            if (EventSystem.current != null) EventSystem.current.RaycastAll(new PointerEventData(EventSystem.current) { position = ecran }, touches);
            return touches.Count > 0;
        }
        public bool Relacher()
        {
            if (retenue == null) return false;
            carte.Demarquer(); retenue = null; return true;
        }

        public void Garder(CelluleDeCarte cellule)
        {
            if (cellule == null) return;
            retenue = cellule;
            // Une terre que la carte ne dessine pas se garde sans marque, et l'ancienne marque tombe.
            if (!carte.Marquer(cellule.CellId, SocleInterface.Couleur("alerte"))) carte.Demarquer();
            // Pendant l'accueil, la terre cliquée montre la fiche de son pays ; seul « Commencer » envoie le choix.
            accueil?.Designer(cellule.CellId);
        }

        // Les sièges des départs conseillés, tant que l'accueil est ouvert sur un monde présent sans maison du joueur ; sinon null.
        IReadOnlyList<long> TerresConseillees()
        {
            var monde = Partie?.Monde;
            if (accueil == null || !accueil.Ouvert || monde == null || !monde.Presente || monde.Donnees.MaisonDuJoueur != null) return null;
            var conseilles = accueil.Conseilles();
            return conseilles.Count == 0 ? null : conseilles.Where(f => f.Siege.CellId != null).Select(f => f.Siege.CellId.Value).ToArray();
        }

        // La phrase du prochain geste, ou null quand la ligne se tait. Le monde s'ouvre en pause : choisir, puis lancer le temps.
        public static string Guide(Lecture<MondeAvecMaisonLu> monde, Lecture<JouablesLus> jouables, RecuIntention recu, HorlogeLue horloge, bool siegeAvecVille)
        {
            if (monde == null || !monde.Presente) return null;
            bool enPause = horloge != null && horloge.JoursParSeconde == 0;
            if (monde.Donnees.MaisonDuJoueur == null)
            {
                if (recu?.Acceptee == true) return enPause ? CHOIX_RECU : null;
                return jouables != null && jouables.Presente ? CHOISIR : null;
            }
            if (!enPause) return null;
            return siegeAvecVille ? LANCER + ENTRER : LANCER;
        }

        static void Detruire(Object o) { if (Application.isPlaying) Destroy(o); else DestroyImmediate(o); }

        void ViderTerres()
        {
            foreach (long terre in terresEclairees) carte.Eteindre(terre);
            terresEclairees.Clear(); ensembleDesTerres = null;
        }

        // Une surbrillance par siège de départ conseillé ; recréées seulement si l'ensemble servi (ou la carte posée) change.
        void AfficherTerres()
        {
            var sieges = TerresConseillees();
            string cle = sieges == null ? null : string.Join(",", sieges.OrderBy(c => c)) + "|" + carte.CellulesServies;
            if (cle != ensembleDesTerres)
            {
                ViderTerres(); ensembleDesTerres = cle;
                if (sieges != null) PoserTerres(sieges);
            }
            // La terre gardée garde son rouge : la marque passe devant l'éclat, qui revient quand elle est relâchée.
            foreach (long terre in terresEclairees) carte.Eclairer(terre, SocleInterface.Couleur("or"));
        }

        // La surbrillance d'une terre de départ est une teinte du terrain lui-même, à l'or du socle : le relief, les bords
        // et les frontières s'y lisent toujours. Un siège dont la carte ne dessine pas la cellule n'en a pas.
        void PoserTerres(IReadOnlyList<long> sieges)
        {
            foreach (long siege in sieges) if (carte.Eclairer(siege, SocleInterface.Couleur("or"))) terresEclairees.Add(siege);
        }

        public void Afficher()
        {
            foreach (Transform enfant in transform) if (enfant.name != "Cabinet" && enfant.gameObject.activeSelf && enfant.GetComponent<Canvas>() != null) enfant.gameObject.SetActive(false);
            date.text = horloge.Absence != null ? "Date indisponible : le monde ne répond pas"
                : horloge.Lue != null ? HorlogeDeCarte.Decrire(horloge.Lue) : "Date en attente du monde";
            foreach (var bouton in temps) bouton.interactable = horloge.Lue != null && horloge.Absence == null;
            temps[1].GetComponentInChildren<Text>().text = horloge.Lue?.JoursParSeconde == 0 ? "Reprendre" : "Pause";
            barre.text = Barre(Partie.Monde, Partie.Comptes);
            jauges.Afficher(Partie.Monde, Partie.Pays);
            etat.gameObject.SetActive(carte.CellulesServies < 0);
            if (carte.CellulesServies < 0) etat.text = carte.TexteAffiche ?? "La carte se prépare…";
            if (retenue != null)
            {
                var monde = Partie.Monde;
                territoire.text = FicheDeCellule.Decrire(retenue, monde == null ? null : monde.Presente
                    ? Lecture<MondeLu>.De(monde.Donnees.Monde) : Lecture<MondeLu>.Absent(monde.Absence));
            }
            else territoire.text = INVITATION;
            string geste = Guide(Partie.Monde, Partie.Jouables, Partie.Recu, horloge.Lue, Partie.Jouable?.Ville.Batie == true);
            guide.gameObject.SetActive(geste != null);
            if (geste != null) guide.text = geste;
            accueil.Afficher();
            dossier.gameObject.SetActive(!accueil.Ouvert); lieu.gameObject.SetActive(!accueil.Ouvert);
            ville.Afficher();
            CentrerSurLeSiege();
            AfficherTerres();
            AfficherMaison();
        }

        // La barre ne montre que des comptes de la maison du joueur servis au tick du monde lu ; sinon elle attend, sans un nombre.
        public static string Barre(Lecture<MondeAvecMaisonLu> monde, Lecture<ComptesDeMaison> comptes)
        {
            if (monde == null) return "Lecture de la maison…";
            if (!monde.Presente) return "Maison indisponible : " + TexteDuMonde.Absence(monde.Absence);
            string id = monde.Donnees.MaisonDuJoueur;
            if (id == null) return "Aucune maison choisie";
            if (comptes == null || comptes.Presente && (comptes.Donnees.Maison.Id != id || comptes.Donnees.Tick != monde.Donnees.Monde.Tick))
                return "Comptes en attente du monde";
            if (!comptes.Presente) return DossierMaison.Indisponible(comptes.Absence);
            var lus = comptes.Donnees;
            return (lus.Maison.Nom ?? TexteDuMonde.Absence(lus.Maison.Absents["nom"])) + " · " + DossierMaison.Prelevement(lus.Part) + " · " + DossierMaison.Grenier(lus.Grenier);
        }

        // Quand la maison du joueur est servie, la vue se pose une fois sur son siège servi ; ensuite le joueur la mène.
        void CentrerSurLeSiege()
        {
            var lue = Partie.Maison;
            if (lue == null || !lue.Presente || lue.Donnees.Id == centreSur || carte.Vue == null || carte.camera == null) return;
            if (!(lue.Donnees.Siege.Position is PointCarte siege) || !(carte.PositionSurLaCarte(siege, 0f) is Vector3 ici)) return;
            centreSur = lue.Donnees.Id;
            carte.Vue.Changer(carte.camera.aspect); carte.Vue.Centrer(new Vector2(ici.x, ici.z), DEMI_SUR_LE_SIEGE_KM); carte.Vue.Poser(carte.camera, carte.transform);
        }

        // « Votre maison » dit la maison servie : son nom, son siège, ses lieux et la date du relevé ; sans maison, elle se tait derrière l'accueil.
        void AfficherMaison()
        {
            var monde = Partie.Monde;
            if (monde == null) return;
            if (!monde.Presente) { EtatsLecture.Afficher(maison, EtatLecture.Panne, monde.Absence); return; }
            maison.color = SocleInterface.Couleur("encre");
            maison.rectTransform.sizeDelta = new Vector2(536, 80);
            if (monde.Donnees.MaisonDuJoueur == null) { maison.text = AccueilDuPays.AUCUN; return; }
            var lue = Partie.Maison;
            if (lue == null || !lue.Presente) { EtatsLecture.Afficher(maison, EtatLecture.Absence, lue?.Absence ?? "Maison en attente"); return; }
            int tenus = lue.Donnees.Lieux.Count; maison.text = (lue.Donnees.Nom ?? TexteDuMonde.Absence(lue.Donnees.Absents["nom"])) + "\nSiège : " + lue.Donnees.Siege.Nom
                + "\n" + TexteDuMonde.Nombre(tenus) + (tenus == 1 ? " lieu tenu" : " lieux tenus") + " · relevé au " + TexteDuMonde.Date(monde.Donnees.Monde.Date);
            maison.rectTransform.sizeDelta = new Vector2(536, 180);
            maison.color = SocleInterface.Couleur("encre");
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
