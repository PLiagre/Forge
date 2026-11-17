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
        public const string TERRES = "Terres conseillées";
        public const string CHOISIR = "Choisissez votre maison : cliquez une terre en surbrillance";
        public const string CHOIX_RECU = "Espace : lancer le temps ; le monde applique votre choix au jour suivant";
        public const string LANCER = "Espace : lancer le temps";
        public const string ENTRER = " · double-clic sur votre siège : entrer dans votre ville";
        public const float HAUTEUR_TERRE = 0.65f; // au-dessus du terrain (0 au plus haut) et des contours (0,5), sous les disques des lieux (0,8) et les noms (1)
        const string INVITATION = "Clic gauche sur une terre pour ouvrir son dossier.";
        public LecturePartie Partie { get; set; }
        public CelluleDeCarte Retenue => retenue;
        CarteDessinee carte;
        HorlogeDeCarte horloge;
        FicheDeCellule fiche;
        GameObject toile;
        Text date, barre, guide, maison, territoire, apercu, etat;
        BarreDuPays jauges;
        Transform terres;
        readonly Dictionary<long, GameObject> terresEclairees = new Dictionary<long, GameObject>();
        readonly List<Object> matieresDeTerre = new List<Object>(); // les maillages et le matériau des surbrillances
        string ensembleDesTerres;
        MonoBehaviour passage; System.Reflection.PropertyInfo siegeLu;
        Transform choix;
        Button confirmer;
        Button[] temps;
        CelluleDeCarte retenue;
        FicheDeDepart candidate;
        RecuIntention recuJournalise;
        string liste;
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
            date = SocleInterface.Texte(bandeau, "Lecture de la date…", 480, 24, 600);
            date.color = SocleInterface.Couleur("papier");
            barre = SocleInterface.Texte(bandeau, "Lecture de la maison…", 24, 72, 1872); // sous le filet, dans les 100 px du bandeau
            barre.color = SocleInterface.Couleur("papier"); barre.rectTransform.sizeDelta = new Vector2(1872, 26);
            // À droite des comptes, au-dessus des jauges, sous les commandes du temps : x 1104 à 1896, y 72 à 98.
            guide = SocleInterface.Texte(bandeau, "", 1104, 72, 792); guide.name = GUIDE;
            guide.rectTransform.sizeDelta = new Vector2(792, 26); guide.alignment = TextAnchor.MiddleRight; guide.color = SocleInterface.Couleur("papier"); guide.raycastTarget = false;
            jauges = new BarreDuPays(bandeau); // sous la barre des comptes, les trois jauges et les trois réserves de points
            temps = new[] { Bouton(bandeau, "Ralentir", 1296, 20, 180, horloge.Ralentir, "Passe le temps du monde à la vitesse inférieure."),
                Bouton(bandeau, "Pause / Reprendre", 1496, 20, 200, horloge.Basculer, "Arrête le temps du monde, ou le relance à la vitesse choisie."),
                Bouton(bandeau, "Accélérer", 1716, 20, 180, horloge.Accelerer, "Passe le temps du monde à la vitesse supérieure.") };
            var dossier = SocleInterface.Panneau(toile.transform, "Votre maison", 1312, 124, 584, 536);
            maison = SocleInterface.Texte(dossier, "Lecture de la partie…", 24, 88, 536);
            gameObject.AddComponent<CommandesMaison>().Initialiser(dossier,
                () => Partie.Monde?.Presente == true ? Partie.Monde.Donnees.MaisonDuJoueur : null,
                LectureDossier.Locale(carte.port), OrdreConfirme.Local(carte.port));
            choix = new GameObject("Maisons proposées", typeof(RectTransform)).transform;
            choix.SetParent(dossier, false);
            var rect = (RectTransform)choix;
            rect.anchorMin = rect.anchorMax = rect.pivot = new Vector2(0, 1);
            apercu = SocleInterface.Texte(dossier, "Consultez une maison avant de vous engager.", 24, 336, 536);
            apercu.rectTransform.sizeDelta = new Vector2(536, 100);
            confirmer = Bouton(dossier, "Choisir cette maison", 24, 468, 536,
                () => { if (candidate != null) _ = Partie.Choisir(candidate.Id); }, "Envoie au monde le choix de la maison consultée ; il l'applique au jour suivant.");
            MatieresCabinet.Engagement(confirmer);
            var lieu = SocleInterface.Panneau(toile.transform, "Territoire conservé", 1312, 684, 584, 372);
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
            var lieux = gameObject.AddComponent<LieuxDeCarte>(); lieux.Installer();
            var fleches = gameObject.AddComponent<FlechesDeCarte>(); fleches.Installer(lieux);
            var guerre = gameObject.AddComponent<CarteDeLaGuerre>(); guerre.Installer(); GetComponent<CalquesCarte>().Brancher(lieux, fleches, guerre);
            gameObject.AddComponent<InfobulleDeTerre>().Initialiser(toile.GetComponent<Canvas>(), LectureDossier.Locale(carte.port), () => fiche.Survolee, LectureDossier.Locale(carte.port)); // la seconde lecture, sur /modificateurs
            terres = new GameObject(TERRES).transform; terres.SetParent(transform, false); // enfant direct de la carte, jamais sous son terrain
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
            // Sans maison, la terre d'une fiche servie est proposée ; seul « Choisir cette maison » envoie le choix.
            var propose = FichesProposees()?.FirstOrDefault(f => f.CellId == cellule.CellId);
            if (propose != null) candidate = propose;
        }

        // Les fiches de départ servies, tant que le monde est présent et sans maison du joueur ; sinon null.
        IReadOnlyList<FicheDeDepart> FichesProposees()
        {
            var monde = Partie?.Monde; var departs = Partie?.Departs;
            return monde != null && monde.Presente && monde.Donnees.MaisonDuJoueur == null && departs != null && departs.Presente ? departs.Donnees.Fiches : null;
        }

        // La phrase du prochain geste, ou null quand la ligne se tait. Le monde s'ouvre en pause : choisir, puis lancer le temps.
        public static string Guide(Lecture<MondeAvecMaisonLu> monde, Lecture<DepartsLus> departs, RecuIntention recu, HorlogeLue horloge, bool siegeAvecVille)
        {
            if (monde == null || !monde.Presente) return null;
            bool enPause = horloge != null && horloge.JoursParSeconde == 0;
            if (monde.Donnees.MaisonDuJoueur == null)
            {
                if (recu?.Acceptee == true) return enPause ? CHOIX_RECU : null;
                return departs != null && departs.Presente ? CHOISIR : null;
            }
            if (!enPause) return null;
            return siegeAvecVille ? LANCER + ENTRER : LANCER;
        }

        // Le siège que le passage à la capitale a lu, rendu par son seul accès `SiegeLu`, relu à chaque image : seul le Zab sert une ville.
        // Le composant n'est pas nommé ici : LesAidesDisentLesNouveauxGestes interdit ce nom dans ce fichier.
        bool SiegeAvecVille()
        {
            if (passage == null) foreach (var m in GetComponents<MonoBehaviour>()) { var p = m == null ? null : m.GetType().GetProperty("SiegeLu"); if (p != null) { passage = m; siegeLu = p; break; } }
            return passage != null && siegeLu.GetValue(passage) != null;
        }

        static void Detruire(Object o) { if (Application.isPlaying) Destroy(o); else DestroyImmediate(o); }

        void ViderTerres()
        {
            foreach (var objet in terresEclairees.Values) if (objet != null) Detruire(objet);
            terresEclairees.Clear();
            foreach (var matiere in matieresDeTerre) if (matiere != null) Detruire(matiere);
            matieresDeTerre.Clear();
            ensembleDesTerres = null;
        }

        // Une surbrillance par terre de départ servie ; recréées seulement si l'ensemble servi (ou la carte posée) change.
        void AfficherTerres()
        {
            var fiches = FichesProposees();
            string cle = fiches == null ? null : string.Join(",", fiches.Select(f => f.CellId).OrderBy(c => c)) + "|" + carte.CellulesServies;
            if (cle != ensembleDesTerres)
            {
                ViderTerres(); ensembleDesTerres = cle;
                if (fiches != null) PoserTerres(fiches);
            }
            foreach (var terre in terresEclairees) terre.Value.SetActive(retenue == null || retenue.CellId != terre.Key);
        }

        // La surbrillance d'une terre est son contour servi, triangulé à plat au-dessus du terrain ; une fiche dont la carte
        // ne dessine pas la cellule n'en a pas.
        void PoserTerres(IReadOnlyList<FicheDeDepart> fiches)
        {
            if (carte.Lue == null || !carte.Origine.HasValue) return;
            var servies = new Dictionary<long, CelluleDeCarte>();
            foreach (var cellule in carte.Lue.Cellules) servies[cellule.CellId] = cellule;
            Material or = null;
            foreach (var fiche in fiches)
            {
                if (terresEclairees.ContainsKey(fiche.CellId) || !servies.TryGetValue(fiche.CellId, out var cellule) || carte.TeinteDe(fiche.CellId) == null) continue;
                var sommets = new List<Vector3>();
                foreach (var polygone in cellule.Contour) sommets.AddRange(TriangulationDeCarte.Trianguler(polygone, carte.Origine.Value).Sommets);
                if (sommets.Count == 0) continue;
                if (or == null) { or = new Material(MateriauDeBase.Prendre()) { name = "Terre conseillée", color = SocleInterface.Couleur("or") }; matieresDeTerre.Add(or); }
                var maillage = new Mesh { name = "Terre conseillée " + fiche.CellId, indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
                maillage.SetVertices(sommets); maillage.SetTriangles(Enumerable.Range(0, sommets.Count).ToArray(), 0); maillage.RecalculateNormals(); maillage.RecalculateBounds(); matieresDeTerre.Add(maillage);
                var objet = new GameObject(maillage.name, typeof(MeshFilter), typeof(MeshRenderer));
                objet.transform.SetParent(terres, false); objet.transform.localPosition = Vector3.up * HAUTEUR_TERRE;
                objet.GetComponent<MeshFilter>().sharedMesh = maillage;
                var rendu = objet.GetComponent<MeshRenderer>(); rendu.sharedMaterial = or;
                rendu.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; rendu.receiveShadows = false;
                terresEclairees.Add(fiche.CellId, objet);
            }
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
            string geste = Guide(Partie.Monde, Partie.Departs, Partie.Recu, horloge.Lue, SiegeAvecVille());
            guide.gameObject.SetActive(geste != null);
            if (geste != null) guide.text = geste;
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
                int tenus = lue.Donnees.Lieux.Count; maison.text = (lue.Donnees.Nom ?? TexteDuMonde.Absence(lue.Donnees.Absents["nom"])) + "\nSiège : " + lue.Donnees.Siege.Nom
                    + "\n" + TexteDuMonde.Nombre(tenus) + (tenus == 1 ? " lieu tenu" : " lieux tenus") + " · relevé au " + TexteDuMonde.Date(monde.Donnees.Monde.Date);
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
                    Bouton(choix, f.Maison, 24 + i % 2 * 276, 168 + i / 2 * 52, 260, () => candidate = f, "Montre l'aperçu de cette maison, sans rien envoyer au monde.");
                    i++;
                }
            }
            foreach (var bouton in choix.GetComponentsInChildren<Button>()) bouton.interactable = Partie.PeutChoisir;
            if (candidate != null) apercu.text = candidate.Nom + " · " + candidate.Siege.Nom
                + "\n" + TexteDuMonde.Nombre(candidate.Habitants) + " habitants autour de " + candidate.Siege.Nom
                + "\nSuzerain : " + (candidate.Suzerain?.Nom ?? "aucun");
            var recu = Partie.Recu;
            if (recu == null) return; // le reçu n'est daté que si l'horloge lue est à son tick ; le tick ne va qu'au journal, une fois par reçu
            if (recu.Acceptee && recu != recuJournalise) { recuJournalise = recu; Debug.Log("CabinetDeCarte : choix reçu au tick " + recu.AppliqueeAuTick); }
            apercu.text = !recu.Acceptee ? (recu.Presente ? "Demande refusée : " + TexteDuMonde.Absence(recu.Erreur) : "Envoi non confirmé : " + TexteDuMonde.Absence(recu.Absence))
                : horloge.Lue?.Tick == recu.AppliqueeAuTick ? "Choix reçu le " + TexteDuMonde.Date(horloge.Lue.Date) + ".\nReprenez le temps : le monde l'appliquera au jour suivant."
                : "Choix reçu ; le monde l'applique au jour suivant.";
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
