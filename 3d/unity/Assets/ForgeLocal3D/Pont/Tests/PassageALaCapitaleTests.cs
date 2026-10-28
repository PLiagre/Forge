using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;
using UnityEngine.UI;
namespace Forge.Pont.Tests
{
    // Lot #689 — la carte mène le joueur à sa capitale quand il confirme une terre qui a un kit, ou lui dit qu'elle n'en a
    // pas encore. Le faux service sert /monde avec la maison du moment, et la fiche figée sur /maison?id=.
    public sealed class PassageALaCapitaleTests
    {
        const int ATTENTE_MS = 10000;
        int port; HttpListener ecoute; Thread fil; readonly List<string> recues = new List<string>();
        string maisonServie; int delaiMs; bool enPanne; // l'état du faux service, remis à chaque cas : NUnit garde l'instance
        GameObject objet; Camera cam; PassageALaCapitale passage; readonly List<string> chargees = new List<string>(); bool vuVisible;
        [SetUp] public void PortLibre()
        {
            var s = new TcpListener(IPAddress.Loopback, 0); s.Start(); port = ((IPEndPoint)s.LocalEndpoint).Port; s.Stop();
            lock (recues) { recues.Clear(); maisonServie = null; delaiMs = 0; enPanne = false; } chargees.Clear(); vuVisible = false;
        }
        [TearDown] public void Fermer()
        {
            passage?.Arreter(); if (objet != null) UnityEngine.Object.DestroyImmediate(objet); if (cam != null) UnityEngine.Object.DestroyImmediate(cam.gameObject);
            ecoute?.Close(); fil?.Join(TimeSpan.FromSeconds(5)); (ecoute, fil, passage) = (null, null, null);
        }
        void Servir()
        {
            // Les fiches sont lues ici : Application.dataPath n'est pas lisible hors du fil principal.
            string zab = Fige("zab"), bar = Fige("bar"), idBar = Id(bar);
            var a = ecoute = new HttpListener(); a.Prefixes.Add("http://127.0.0.1:" + port + "/"); a.Start();
            (fil = new Thread(() => { try { while (true) { var c = a.GetContext(); string url = c.Request.RawUrl; string maison; int delai; bool panne;
                lock (recues) { recues.Add(c.Request.HttpMethod + " " + url); maison = maisonServie; delai = delaiMs; panne = enPanne; }
                if (delai > 0) Thread.Sleep(delai);
                string fiche = maison == idBar ? bar : zab;
                (int st, string tx) = url.StartsWith("/maison?id=", StringComparison.Ordinal) ? (200, fiche) : url != "/monde" ? (404, "{}") : panne ? (500, "{\"erreur\":\"panne\"}") : (200, Monde(maison));
                c.Response.StatusCode = st; c.Response.Close(Encoding.UTF8.GetBytes(tx), true); } } catch (Exception) { } }) { IsBackground = true }).Start();
        }
        void Servir(string maison) { lock (recues) maisonServie = maison; }
        string[] Recues() { lock (recues) return recues.ToArray(); }
        int Mondes() => Recues().Count(r => r == "GET /monde");
        static string Monde(string maison) => "{\"tick\":0,\"date\":{\"annee\":1400,\"jour_de_l_annee\":1},\"cell_count\":1,\"cells\":[{\"cell_id\":7,\"population\":1,\"hunger_ticks\":0,\"food_deficit_kg\":0}]" + (maison == null ? "" : ",\"maison_du_joueur\":\"" + maison + "\"") + "}";
        static string Fige(string terre) => Encoding.UTF8.GetString(File.ReadAllBytes(Path.Combine(Application.dataPath, "ForgeLocal3D/Pont/Tests/maison-" + terre + "-graine0-tick0.json")));
        static string Zab => Id(Fige("zab")); static string Bar => Id(Fige("bar")); static string Id(string fiche) => (string)LecteurJson.LireObjet(fiche)["id"];
        void Poser(GameObject enfant = null)
        {
            cam = new GameObject("Caméra du test").AddComponent<Camera>();
            objet = new GameObject("Carte du test"); enfant?.transform.SetParent(objet.transform, false);
            passage = objet.AddComponent<PassageALaCapitale>(); passage.port = port; passage.ChargerScene = nom => chargees.Add(nom); passage.Demarrer(cam);
        }
        // Quelques pas, chacun après la fin de la lecture en vol, puis un dernier qui applique la lecture finie sans en lancer.
        void Pas(ref double instant, int tours)
        {
            for (int tour = 0; tour < tours; tour++)
            {
                passage.Pas(instant); vuVisible |= passage.PanneauVisible; instant += PassageALaCapitale.PERIODE_LECTURE_S; Attendre();
            }
            passage.Pas(instant - PassageALaCapitale.PERIODE_LECTURE_S / 2); vuVisible |= passage.PanneauVisible;
        }
        void Attendre()
        {
            var montre = Stopwatch.StartNew(); while (passage.RequeteEnVol && montre.ElapsedMilliseconds < ATTENTE_MS) Thread.Sleep(5);
            Assert.IsFalse(passage.RequeteEnVol, "la lecture n'a pas fini");
        }
        [Test] public void LeZabConfirmeOuvreLeKsarUneSeuleFois()
        {
            string scene = TerresAvecKit.Scenes[Zab];
            Servir(); Poser(); double t = 1; Pas(ref t, 2);
            CollectionAssert.IsEmpty(chargees, "la ville s'est ouverte avant la confirmation");
            // Le compte est relevé dans la demande même : une lecture lancée pendant ce pas arriverait après lui.
            int lus = -1; bool enVol = true;
            passage.ChargerScene = nom => { chargees.Add(nom); lus = Mondes(); enVol = passage.RequeteEnVol; };
            Servir(Zab); Pas(ref t, 4);
            CollectionAssert.AreEqual(new[] { scene }, chargees); Assert.AreEqual(scene, passage.SceneDemandee);
            Assert.IsFalse(enVol, "une lecture était en vol à la demande");
            Pas(ref t, 4); Thread.Sleep(200); // le temps qu'une lecture lâchée sans suivi atteigne le service
            CollectionAssert.AreEqual(new[] { scene }, chargees, "la scène est rechargée");
            Assert.AreEqual(lus, Mondes(), "une lecture est partie après la demande : " + string.Join(", ", Recues()));
            Assert.IsFalse(vuVisible, "le panneau s'est montré pour une terre qui a un kit");
        }
        [Test] public void BarAfficheLePanneauQuiSurvitAuCabinet()
        {
            var temoin = new GameObject("Toile témoin", typeof(RectTransform)); temoin.AddComponent<Canvas>();
            Servir(); Poser(temoin); double t = 1; Pas(ref t, 2);
            Assert.IsFalse(passage.PanneauVisible);
            Servir(Bar); Pas(ref t, 3);
            Assert.IsTrue(passage.PanneauVisible); Assert.AreEqual(PassageALaCapitale.MESSAGE_SANS_KIT, passage.TexteAffiche);
            CollectionAssert.IsEmpty(chargees); Assert.IsNull(passage.SceneDemandee);
            // Le geste de CabinetDeCarte.Construire : il cache toutes les toiles de l'objet de la carte.
            foreach (var ancienne in objet.GetComponentsInChildren<Canvas>()) ancienne.gameObject.SetActive(false);
            Assert.IsFalse(temoin.activeInHierarchy, "le geste du cabinet n'a pas porté");
            var toiles = UnityEngine.Object.FindObjectsByType<Canvas>(FindObjectsSortMode.None).Where(c => c.worldCamera == cam).ToArray();
            Assert.AreEqual(1, toiles.Length, "la toile du panneau a disparu avec celles du cabinet");
            Canvas toile = toiles[0];
            Assert.IsTrue(toile.gameObject.activeInHierarchy && toile.transform.parent == null && toile.renderMode == RenderMode.ScreenSpaceCamera, toile.renderMode.ToString());
            Assert.IsTrue(passage.PanneauVisible);
            var echelle = toile.GetComponent<CanvasScaler>();
            Assert.IsTrue(echelle.uiScaleMode == CanvasScaler.ScaleMode.ScaleWithScreenSize && echelle.referenceResolution == new Vector2(1920, 1080) && echelle.matchWidthOrHeight == 0, echelle.uiScaleMode + " " + echelle.referenceResolution);
            var cadre = toile.GetComponentInChildren<Image>().rectTransform;
            Assert.IsTrue(cadre.anchorMin == Vector2.one && cadre.anchorMax == Vector2.one && cadre.pivot == Vector2.one, cadre.anchorMin + " " + cadre.pivot);
            const float CAMERA = 0.67f * 1920; // CabinetDeCarte.cs : carte.camera.rect = new Rect(0, 0, .67f, 1)
            const float FIN_DES_FEUILLETS = 24 + 740; // Feuillet.cs : SocleInterface.Panneau(parent, titre, 24, 124, 740, 760)
            const float BANDEAU = 100; // CabinetDeCarte.cs : Panneau(toile.transform, "FORGE · Le cabinet", 0, 0, 1920, 100)
            const float GUIDE = 872; // CabinetDeCarte.cs : Panneau(toile.transform, "Parcourir le monde", 24, 872, 1238, 184)
            Assert.GreaterOrEqual(CAMERA + cadre.anchoredPosition.x - cadre.sizeDelta.x, FIN_DES_FEUILLETS, "le panneau couvre les feuillets");
            Assert.GreaterOrEqual(-cadre.anchoredPosition.y, BANDEAU, "le panneau couvre le bandeau");
            Assert.LessOrEqual(-cadre.anchoredPosition.y + cadre.sizeDelta.y, GUIDE, "le panneau couvre le guide");
        }
        [Test] public void UnZabDejaConfirmeNeRenvoiePasEnVille()
        {
            Servir(Zab); Servir(); Poser(); double t = 1; Pas(ref t, 5);
            CollectionAssert.IsEmpty(chargees, "un Zab déjà confirmé renvoie en ville"); Assert.IsNull(passage.SceneDemandee);
            Assert.IsFalse(vuVisible); Assert.GreaterOrEqual(Mondes(), 1, "le monde n'a pas été lu");
        }
        [Test] public void UnBarDejaConfirmeMontreLePanneauPuisUnDepartLeCache()
        {
            Servir(Bar); Servir(); Poser(); double t = 1; Pas(ref t, 2);
            Assert.IsTrue(passage.PanneauVisible); Assert.AreEqual(PassageALaCapitale.MESSAGE_SANS_KIT, passage.TexteAffiche);
            Servir(null); Pas(ref t, 2);
            Assert.IsFalse(passage.PanneauVisible); CollectionAssert.IsEmpty(chargees);
        }
        [Test] public void UneAbsenceNArmeRien()
        {
            Poser(); double t = 1; Pas(ref t, 3);
            Assert.IsNotNull(passage.Absence); StringAssert.StartsWith("monde : ", passage.Absence); Assert.IsFalse(passage.PanneauVisible);
            Servir(Zab); Servir(); Pas(ref t, 4);
            CollectionAssert.IsEmpty(chargees, "une absence a été prise pour un départ"); Assert.IsNull(passage.Absence);
            Assert.GreaterOrEqual(Mondes(), 1, "le service revenu n'a pas été lu");
        }
        [Test] public void UneAbsenceGardeLeDepartVu()
        {
            string scene = TerresAvecKit.Scenes[Zab];
            Servir(); Poser(); double t = 1; Pas(ref t, 2);
            lock (recues) enPanne = true; Pas(ref t, 2);
            StringAssert.StartsWith("monde : ", passage.Absence); StringAssert.Contains("statut 500", passage.Absence); CollectionAssert.IsEmpty(chargees);
            lock (recues) { maisonServie = Zab; enPanne = false; } Pas(ref t, 4); // sans lecture Depart entre la panne et le Zab
            CollectionAssert.AreEqual(new[] { scene }, chargees, "l'absence a désarmé le départ vu"); Assert.AreEqual(scene, passage.SceneDemandee);
        }
        [Test] public void UneAbsenceLaisseLePanneauMontre()
        {
            Servir(Bar); Servir(); Poser(); double t = 1; Pas(ref t, 2);
            Assert.IsTrue(passage.PanneauVisible);
            lock (recues) enPanne = true; Pas(ref t, 3);
            StringAssert.StartsWith("monde : ", passage.Absence); StringAssert.Contains("statut 500", passage.Absence);
            Assert.IsTrue(passage.PanneauVisible, "une absence a caché le panneau"); Assert.AreEqual(PassageALaCapitale.MESSAGE_SANS_KIT, passage.TexteAffiche);
            CollectionAssert.IsEmpty(chargees);
        }
        [Test] public void UneLectureLenteNeBloquePasLesPas()
        {
            lock (recues) delaiMs = 500; Servir(); Poser();
            var montre = Stopwatch.StartNew();
            for (int i = 0; i < 10; i++) passage.Pas(1 + i * PassageALaCapitale.PERIODE_LECTURE_S);
            long ecoule = montre.ElapsedMilliseconds;
            Assert.Less(ecoule, 200, "les pas attendent la lecture");
            Attendre();
            Assert.AreEqual(1, Mondes(), string.Join(", ", Recues()));
        }
        [Test] public void UneLectureRapideAttendSaPeriode()
        {
            const double DEBUT = 1, ECHEANCE = DEBUT + PassageALaCapitale.PERIODE_LECTURE_S;
            Servir(); Poser();
            passage.Pas(DEBUT); Attendre(); Assert.AreEqual(1, Mondes());
            // La lecture est finie bien avant la seconde : les pas qui la précèdent l'appliquent sans en relancer.
            foreach (double avant in new[] { DEBUT, DEBUT + 0.25, DEBUT + 0.5, ECHEANCE - 0.001 })
            { passage.Pas(avant); Assert.IsFalse(passage.RequeteEnVol, "une lecture est repartie à " + avant); }
            Thread.Sleep(200); Assert.AreEqual(1, Mondes(), "une lecture est partie avant l'échéance : " + string.Join(", ", Recues()));
            passage.Pas(ECHEANCE); Attendre(); Assert.AreEqual(2, Mondes(), "aucune lecture à l'échéance");
            passage.Pas(ECHEANCE + 0.5); Thread.Sleep(200); Assert.AreEqual(2, Mondes(), "une lecture est partie avant la seconde échéance");
        }
        [Test] public void SansCameraRienNePart()
        {
            Servir(Zab); Servir();
            objet = new GameObject("Carte sans caméra"); passage = objet.AddComponent<PassageALaCapitale>(); passage.port = port; passage.ChargerScene = nom => chargees.Add(nom);
            LogAssert.Expect(LogType.Error, "PassageALaCapitale : pas de caméra, le passage ne lit rien");
            passage.Demarrer(null);
            for (int i = 0; i < 5; i++) { passage.Pas(1 + i * PassageALaCapitale.PERIODE_LECTURE_S); Assert.IsFalse(passage.RequeteEnVol); }
            Thread.Sleep(100);
            CollectionAssert.IsEmpty(Recues()); CollectionAssert.IsEmpty(chargees); Assert.IsFalse(passage.PanneauVisible);
        }
        // Lot #701 — la remise : le siège lu dans /maison, retenu pour la scène demandée, pris une seule fois.
        static long SiegeDuZab => (long)(double)((Dictionary<string, object>)LecteurJson.LireObjet(Fige("zab"))["siege"])["cell_id"];
        [Test] public void LeZabConfirmeRemetSonSiegeUneSeuleFois()
        {
            PassageALaCapitale.PrendreCelluleRemise(string.Empty); long? remise = null, seconde = -1;
            Servir(); Poser(); double t = 1; Pas(ref t, 2);
            passage.ChargerScene = nom => { chargees.Add(nom); remise = PassageALaCapitale.PrendreCelluleRemise(nom); seconde = PassageALaCapitale.PrendreCelluleRemise(nom); };
            Servir(Zab); Pas(ref t, 4);
            CollectionAssert.AreEqual(new[] { TerresAvecKit.Scenes[Zab] }, chargees);
            Assert.AreEqual(SiegeDuZab, remise, "la remise ne porte pas le siège servi"); Assert.IsNull(seconde, "la remise sert deux fois");
        }
        [Test] public void UneAutreSceneNePrendRienEtEfface()
        {
            PassageALaCapitale.PrendreCelluleRemise(string.Empty); long? autre = -1, apres = -1;
            Servir(); Poser(); double t = 1; Pas(ref t, 2);
            passage.ChargerScene = nom => { chargees.Add(nom); autre = PassageALaCapitale.PrendreCelluleRemise("AutreTerre"); apres = PassageALaCapitale.PrendreCelluleRemise(nom); };
            Servir(Zab); Pas(ref t, 4);
            Assert.AreEqual(1, chargees.Count); Assert.IsNull(autre, "une autre scène a pris la remise"); Assert.IsNull(apres, "la prise d'une autre scène n'a pas effacé la remise");
        }
        [TestCase("bar")] [TestCase("zab-deja")] [TestCase("absence")]
        public void SansConfirmationVueRienNEstRemis(string cas)
        {
            PassageALaCapitale.PrendreCelluleRemise(string.Empty); double t = 1;
            if (cas == "bar") { Servir(); Poser(); Pas(ref t, 2); Servir(Bar); Pas(ref t, 3); }
            else if (cas == "zab-deja") { Servir(Zab); Servir(); Poser(); Pas(ref t, 5); }
            else { Poser(); Pas(ref t, 3); }
            CollectionAssert.IsEmpty(chargees, cas); Assert.IsNull(PassageALaCapitale.PrendreCelluleRemise(TerresAvecKit.Scenes[Zab]), cas);
        }
        // Lot #690 — le rappel de chargement, sur des scènes temporaires jamais enregistrées. CreateScene n'existe qu'en jeu.
        [UnityTest] public IEnumerator LeChargementPoseLePassageSurLaSeuleCarte()
        {
            UnityEditor.SceneManagement.EditorSceneManager.NewScene(UnityEditor.SceneManagement.NewSceneSetup.EmptyScene);
            yield return new EnterPlayMode();
            var notes = new List<string>(); const int PORT = 4242;
            (Scene scene, GameObject carte) = SceneDe(OuvertureDeLaCarte.SCENE, true);
            try {
                carte.GetComponent<CarteDessinee>().port = PORT; PassageALaCapitale.AuChargement(scene, LoadSceneMode.Single);
                PassageALaCapitale pose = carte.GetComponent<PassageALaCapitale>();
                if (pose == null) notes.Add("carte : la carte n'a pas reçu de passage");
                else if (pose.port != PORT) notes.Add("carte : le passage n'a pas le port de la carte");
                else { PassageALaCapitale.AuChargement(scene, LoadSceneMode.Single); PassageALaCapitale[] tous = carte.GetComponents<PassageALaCapitale>();
                    if (tous.Length != 1 || !ReferenceEquals(pose, tous[0]) || tous[0].port != PORT) notes.Add("carte : un second chargement a créé ou remplacé le passage"); }
            } catch (Exception e) { notes.Add("carte : " + e.Message); }
            for (IEnumerator d = Decharger(scene); d.MoveNext();) yield return null;
            (scene, carte) = SceneDe(OuvertureDeLaCarte.SCENE, true);
            try { PassageALaCapitale deja = carte.AddComponent<PassageALaCapitale>(); deja.port = 7; carte.GetComponent<CarteDessinee>().port = 9999;
                PassageALaCapitale.AuChargement(scene, LoadSceneMode.Single); PassageALaCapitale[] gardes = carte.GetComponents<PassageALaCapitale>();
                if (gardes.Length != 1 || !ReferenceEquals(deja, gardes[0]) || deja.port != 7) notes.Add("déjà présent : le passage n'a pas été conservé");
            } catch (Exception e) { notes.Add("déjà présent : " + e.Message); }
            for (IEnumerator d = Decharger(scene); d.MoveNext();) yield return null;
            (scene, carte) = SceneDe("AutreTerre", true);
            try { PassageALaCapitale.AuChargement(scene, LoadSceneMode.Single);
                if (carte.GetComponent<PassageALaCapitale>() != null) notes.Add("autre scène : une carte hors Forge_Carte a reçu un passage");
            } catch (Exception e) { notes.Add("autre scène : " + e.Message); }
            for (IEnumerator d = Decharger(scene); d.MoveNext();) yield return null;
            GameObject objet; (scene, objet) = SceneDe(OuvertureDeLaCarte.SCENE, false);
            try { PassageALaCapitale.AuChargement(scene, LoadSceneMode.Single);
                if (objet.GetComponent<PassageALaCapitale>() != null || scene.GetRootGameObjects().Any(o => o.GetComponentInChildren<PassageALaCapitale>(true) != null))
                    notes.Add("sans carte : la scène a reçu un passage");
            } catch (Exception e) { notes.Add("sans carte : " + e.Message); }
            for (IEnumerator d = Decharger(scene); d.MoveNext();) yield return null;
            // Deux scènes chargées ensemble : la carte de la scène voisine n'appartient pas à Forge_Carte.
            (Scene voisine, GameObject etrangere) = SceneDe("Voisine", true); (scene, carte) = SceneDe(OuvertureDeLaCarte.SCENE, true);
            try { PassageALaCapitale.AuChargement(scene, LoadSceneMode.Additive);
                if (carte.GetComponent<PassageALaCapitale>() == null) notes.Add("scène voisine : la carte de Forge_Carte n'a pas reçu de passage");
                if (etrangere.GetComponent<PassageALaCapitale>() != null) notes.Add("scène voisine : une carte d'une autre scène chargée a reçu un passage");
            } catch (Exception e) { notes.Add("scène voisine : " + e.Message); }
            for (IEnumerator d = Decharger(scene); d.MoveNext();) yield return null;
            for (IEnumerator d = Decharger(voisine); d.MoveNext();) yield return null;
            if (notes.Count > 0) Assert.Fail(string.Join(" | ", notes));
            yield return new ExitPlayMode();
        }
        static IEnumerator Decharger(Scene scene)
        {
            if (!scene.IsValid() || !scene.isLoaded) yield break;
            foreach (GameObject racine in scene.GetRootGameObjects()) racine.SetActive(false);
            for (int i = 0; i < SceneManager.sceneCount; i++) { Scene autre = SceneManager.GetSceneAt(i); if (autre != scene && autre.isLoaded) { SceneManager.SetActiveScene(autre); break; } }
            AsyncOperation op = SceneManager.UnloadSceneAsync(scene); while (op != null && !op.isDone) yield return null;
        }
        static (Scene, GameObject) SceneDe(string nom, bool avecCarte)
        {
            Scene scene = SceneManager.CreateScene(nom); var objet = new GameObject(avecCarte ? "Carte temporaire" : "Sans carte");
            SceneManager.MoveGameObjectToScene(objet, scene); if (avecCarte) objet.AddComponent<CarteDessinee>(); SceneManager.SetActiveScene(scene);
            return (scene, objet);
        }
        // Lot #729 — un double-clic sur le siège lu descend comme la confirmation, une seule fois ; rien d'autre ne descend.
        static long SiegeDe(string terre) => (long)(double)((Dictionary<string, object>)LecteurJson.LireObjet(Fige(terre))["siege"])["cell_id"];
        [Test] public void UnDoubleClicSurLeSiegeDescendUneSeuleFois()
        {
            PassageALaCapitale.PrendreCelluleRemise(string.Empty); string scene = TerresAvecKit.Scenes[Zab];
            Servir(Zab); Servir(); Poser(); double t = 1; Pas(ref t, 3);
            Assert.AreEqual(SiegeDuZab, passage.SiegeLu, "le siège lu n'est pas celui de la fiche"); CollectionAssert.IsEmpty(chargees);
            Assert.IsFalse(passage.Cliquer(SiegeDuZab, t), "un clic seul descend");
            Assert.IsTrue(passage.Cliquer(SiegeDuZab, t + 0.2), "le double-clic sur le siège ne descend pas");
            CollectionAssert.AreEqual(new[] { scene }, chargees); Assert.AreEqual(scene, passage.SceneDemandee);
            Assert.AreEqual(SiegeDuZab, PassageALaCapitale.PrendreCelluleRemise(scene), "la remise ne porte pas le siège");
            int lus = Mondes(); Pas(ref t, 3); Thread.Sleep(200); // le temps qu'une lecture lâchée sans suivi atteigne le service
            Assert.AreEqual(lus, Mondes(), "une lecture est partie après la descente : " + string.Join(", ", Recues()));
            bool troisieme = passage.Cliquer(SiegeDuZab, t), quatrieme = passage.Cliquer(SiegeDuZab, t + 0.2);
            Assert.IsFalse(troisieme || quatrieme, "un second double-clic a rendu true"); CollectionAssert.AreEqual(new[] { scene }, chargees, "la scène est rechargée");
        }
        [TestCase("un-clic")] [TestCase("lent")] [TestCase("autre-cellule")] [TestCase("bar")] [TestCase("depart")] [TestCase("absence")]
        public void RienDAutreNeDescend(string cas)
        {
            PassageALaCapitale.PrendreCelluleRemise(string.Empty); double t = 1; bool zab = cas == "un-clic" || cas == "lent" || cas == "autre-cellule";
            if (cas != "absence") { Servir(zab ? Zab : cas == "bar" ? Bar : null); Servir(); }
            Poser(); Pas(ref t, 3);
            Assert.AreEqual(zab ? SiegeDuZab : (long?)null, passage.SiegeLu, cas + " : siège lu");
            long siege = SiegeDe(cas == "bar" ? "bar" : "zab");
            bool descendu = passage.Cliquer(siege, t);
            if (cas != "un-clic") descendu |= passage.Cliquer(cas == "autre-cellule" ? siege + 1 : siege, t + (cas == "lent" ? PassageALaCapitale.DELAI_DOUBLE_CLIC_S + 0.01 : 0.2));
            if (cas == "autre-cellule") descendu |= passage.Cliquer(siege + 1, t + 1) | passage.Cliquer(siege + 1, t + 1.2); // deux clics sur la même cellule, hors du siège
            Assert.IsFalse(descendu, cas + " : un clic a rendu true"); CollectionAssert.IsEmpty(chargees, cas); Assert.IsNull(passage.SceneDemandee, cas);
            Assert.IsNull(PassageALaCapitale.PrendreCelluleRemise(TerresAvecKit.Scenes[Zab]), cas + " : une remise est faite");
        }
        [TestCase("confirmation")] [TestCase("double-clic")]
        public void ParDefautLePassagePrendLaTransition(string cas)
        {
            string scene = TerresAvecKit.Scenes[Zab]; double t = 1;
            if (cas == "double-clic") Servir(Zab); Servir(); Poser(); passage.ChargerScene = null;
            if (cas == "confirmation") { Pas(ref t, 2); Servir(Zab); Pas(ref t, 4); }
            else { Pas(ref t, 3); passage.Cliquer(SiegeDuZab, t); Assert.IsTrue(passage.Cliquer(SiegeDuZab, t + 0.2), "le double-clic ne descend pas"); }
            TransitionDeVue[] transitions = UnityEngine.Object.FindObjectsByType<TransitionDeVue>(FindObjectsSortMode.None);
            try {
                Assert.AreEqual(1, transitions.Length, cas + " : transitions dans la scène"); TransitionDeVue transition = transitions[0];
                Assert.IsTrue(transition.EnCours, cas); Assert.AreEqual(port, transition.port, cas + " : port"); Assert.IsNull(transition.SceneChargee, cas); Assert.AreEqual(scene, passage.SceneDemandee, cas);
                var vues = new List<string>(); transition.ChargerScene = nom => vues.Add(nom);
                transition.Pas(Time.realtimeSinceStartupAsDouble + TransitionDeVue.DUREE_FONDU_S + 0.1);
                CollectionAssert.AreEqual(new[] { scene }, vues, cas + " : scène chargée par la transition");
            } finally { foreach (TransitionDeVue transition in transitions) { transition.Arreter(); UnityEngine.Object.DestroyImmediate(transition.gameObject); } }
        }
    }
}
