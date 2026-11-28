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
    // La carte mène le joueur à sa capitale quand il le demande (`Entrer`, ou un double-clic sur le siège lu), jamais
    // d'elle-même. Le faux service sert /monde avec la maison du moment, et la fiche figée sur /maison?id=.
    public sealed class PassageALaCapitaleTests
    {
        const int ATTENTE_MS = 10000;
        int port; HttpListener ecoute; Thread fil; readonly List<string> recues = new List<string>();
        string maisonServie; int delaiMs; bool enPanne; // l'état du faux service, remis à chaque cas : NUnit garde l'instance
        GameObject objet; Camera cam; PassageALaCapitale passage; readonly List<string> chargees = new List<string>();
        [SetUp] public void PortLibre()
        {
            var s = new TcpListener(IPAddress.Loopback, 0); s.Start(); port = ((IPEndPoint)s.LocalEndpoint).Port; s.Stop();
            lock (recues) { recues.Clear(); maisonServie = null; delaiMs = 0; enPanne = false; } chargees.Clear();
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
                passage.Pas(instant); instant += PassageALaCapitale.PERIODE_LECTURE_S; Attendre();
            }
            passage.Pas(instant - PassageALaCapitale.PERIODE_LECTURE_S / 2);
        }
        void Attendre()
        {
            var montre = Stopwatch.StartNew(); while (passage.RequeteEnVol && montre.ElapsedMilliseconds < ATTENTE_MS) Thread.Sleep(5);
            Assert.IsFalse(passage.RequeteEnVol, "la lecture n'a pas fini");
        }
        // La confirmation d'une terre qui a sa ville ne descend plus : le siège se lit, la ville attend le geste du joueur.
        [Test] public void LaConfirmationDuZabNOuvreRienEtLitSonSiege()
        {
            Servir(); Poser(); double t = 1; Pas(ref t, 2);
            Assert.IsNull(passage.SiegeLu, "un siège est lu avant le choix");
            Servir(Zab); Pas(ref t, 4);
            CollectionAssert.IsEmpty(chargees, "la confirmation a ouvert la ville"); Assert.IsNull(passage.SceneDemandee);
            Assert.AreEqual(SiegeDuZab, passage.SiegeLu, "le siège servi n'est pas lu");
            Assert.GreaterOrEqual(Mondes(), 3, "le monde n'est plus relu");
        }
        [Test] public void EntrerOuvreLeKsarUneSeuleFoisEtNeLitPlusRien()
        {
            string scene = TerresAvecKit.Scenes[Zab];
            Servir(Zab); Servir(); Poser(); double t = 1; Pas(ref t, 2);
            // Le compte est relevé dans la demande même : une lecture lancée pendant ce pas arriverait après lui.
            int lus = -1; bool enVol = true;
            passage.ChargerScene = nom => { chargees.Add(nom); lus = Mondes(); enVol = passage.RequeteEnVol; };
            Assert.IsTrue(passage.Entrer(scene, SiegeDuZab), "Entrer ne descend pas");
            CollectionAssert.AreEqual(new[] { scene }, chargees); Assert.AreEqual(scene, passage.SceneDemandee);
            Assert.IsFalse(enVol, "une lecture était suivie à la demande");
            Assert.IsFalse(passage.Entrer(scene, SiegeDuZab), "un second Entrer descend"); Assert.IsFalse(passage.Cliquer(SiegeDuZab, t) | passage.Cliquer(SiegeDuZab, t + 0.2), "un double-clic descend après Entrer");
            Pas(ref t, 4); Thread.Sleep(200); // le temps qu'une lecture lâchée sans suivi atteigne le service
            CollectionAssert.AreEqual(new[] { scene }, chargees, "la scène est rechargée");
            Assert.AreEqual(lus, Mondes(), "une lecture est partie après la demande : " + string.Join(", ", Recues()));
        }
        [TestCase(null)] [TestCase("")]
        public void EntrerSansSceneNeDescendPas(string scene)
        {
            Servir(Zab); Servir(); Poser(); double t = 1; Pas(ref t, 2);
            Assert.IsFalse(passage.Entrer(scene, SiegeDuZab)); CollectionAssert.IsEmpty(chargees); Assert.IsNull(passage.SceneDemandee);
        }
        [Test] public void UnBarConfirmeNeLitAucunSiegeEtNOuvreRien()
        {
            Servir(Bar); Servir(); Poser(); double t = 1; Pas(ref t, 3);
            Assert.IsNull(passage.SiegeLu, "Bar n'a pas de ville : aucun siège ne descend"); CollectionAssert.IsEmpty(chargees); Assert.IsNull(passage.SceneDemandee);
            Assert.IsFalse(passage.Cliquer(SiegeDe("bar"), t) | passage.Cliquer(SiegeDe("bar"), t + 0.2), "le double-clic sur le siège de Bar descend");
        }
        [Test] public void UneAbsenceNArmeRien()
        {
            Poser(); double t = 1; Pas(ref t, 3);
            Assert.IsNotNull(passage.Absence); StringAssert.StartsWith("monde : ", passage.Absence); Assert.IsNull(passage.SiegeLu);
            Servir(Zab); Servir(); Pas(ref t, 4);
            CollectionAssert.IsEmpty(chargees, "une absence a ouvert la ville"); Assert.IsNull(passage.Absence);
            Assert.GreaterOrEqual(Mondes(), 1, "le service revenu n'a pas été lu");
        }
        [Test] public void UneAbsenceGardeLeSiegeLu()
        {
            Servir(Zab); Servir(); Poser(); double t = 1; Pas(ref t, 2);
            Assert.AreEqual(SiegeDuZab, passage.SiegeLu);
            lock (recues) enPanne = true; Pas(ref t, 2);
            StringAssert.StartsWith("monde : ", passage.Absence); StringAssert.Contains("statut 500", passage.Absence); CollectionAssert.IsEmpty(chargees);
            Assert.AreEqual(SiegeDuZab, passage.SiegeLu, "l'absence a effacé le siège lu");
            Assert.IsTrue(passage.Cliquer(SiegeDuZab, t) | passage.Cliquer(SiegeDuZab, t + 0.2), "le double-clic ne descend plus pendant la panne");
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
            CollectionAssert.IsEmpty(Recues()); CollectionAssert.IsEmpty(chargees); Assert.IsNull(passage.SiegeLu);
        }
        // La remise : le siège lu dans /maison, retenu pour la scène demandée, pris une seule fois.
        static long SiegeDuZab => (long)(double)((Dictionary<string, object>)LecteurJson.LireObjet(Fige("zab"))["siege"])["cell_id"];
        [Test] public void EntrerRemetLeSiegeUneSeuleFois()
        {
            PassageALaCapitale.PrendreCelluleRemise(string.Empty); long? remise = null, seconde = -1;
            Servir(Zab); Servir(); Poser(); double t = 1; Pas(ref t, 2);
            passage.ChargerScene = nom => { chargees.Add(nom); remise = PassageALaCapitale.PrendreCelluleRemise(nom); seconde = PassageALaCapitale.PrendreCelluleRemise(nom); };
            Assert.IsTrue(passage.Entrer(TerresAvecKit.Scenes[Zab], SiegeDuZab));
            CollectionAssert.AreEqual(new[] { TerresAvecKit.Scenes[Zab] }, chargees);
            Assert.AreEqual(SiegeDuZab, remise, "la remise ne porte pas le siège donné"); Assert.IsNull(seconde, "la remise sert deux fois");
        }
        [Test] public void UneAutreSceneNePrendRienEtEfface()
        {
            PassageALaCapitale.PrendreCelluleRemise(string.Empty); long? autre = -1, apres = -1;
            Servir(Zab); Servir(); Poser(); double t = 1; Pas(ref t, 2);
            passage.ChargerScene = nom => { chargees.Add(nom); autre = PassageALaCapitale.PrendreCelluleRemise("AutreTerre"); apres = PassageALaCapitale.PrendreCelluleRemise(nom); };
            Assert.IsTrue(passage.Entrer(TerresAvecKit.Scenes[Zab], SiegeDuZab));
            Assert.AreEqual(1, chargees.Count); Assert.IsNull(autre, "une autre scène a pris la remise"); Assert.IsNull(apres, "la prise d'une autre scène n'a pas effacé la remise");
        }
        [TestCase("bar")] [TestCase("zab-deja")] [TestCase("zab-confirme")] [TestCase("absence")]
        public void SansGesteRienNEstRemis(string cas)
        {
            PassageALaCapitale.PrendreCelluleRemise(string.Empty); double t = 1;
            if (cas == "bar") { Servir(); Poser(); Pas(ref t, 2); Servir(Bar); Pas(ref t, 3); }
            else if (cas == "zab-deja") { Servir(Zab); Servir(); Poser(); Pas(ref t, 5); }
            else if (cas == "zab-confirme") { Servir(); Poser(); Pas(ref t, 2); Servir(Zab); Pas(ref t, 4); }
            else { Poser(); Pas(ref t, 3); }
            CollectionAssert.IsEmpty(chargees, cas); Assert.IsNull(PassageALaCapitale.PrendreCelluleRemise(TerresAvecKit.Scenes[Zab]), cas);
        }
        // Le rappel de chargement, sur des scènes temporaires jamais enregistrées. CreateScene n'existe qu'en jeu.
        [UnityTest] public IEnumerator LeChargementPoseLePassageSurLaSeuleCarte()
        {
            UnityEditor.SceneManagement.EditorSceneManager.NewScene(UnityEditor.SceneManagement.NewSceneSetup.EmptyScene);
            yield return new EnterPlayMode();
            var notes = new List<string>(); const int PORT = 4242;
            (Scene scene, GameObject carte) = SceneDe(OuvertureDeLaCarte.SCENE, true);
            try {
                carte.GetComponent<CarteDessinee>().port = PORT; var avant = new HashSet<Component>(carte.GetComponents<Component>());
                PassageALaCapitale.AuChargement(scene, LoadSceneMode.Single);
                PassageALaCapitale pose = carte.GetComponent<PassageALaCapitale>();
                // Le passage ne pose que lui : la capitale du joueur n'est nommée que par les villes de la carte, jamais une seconde fois.
                var autres = carte.GetComponents<Component>().Where(c => !avant.Contains(c) && !(c is PassageALaCapitale)).Select(c => c.GetType().Name).ToList();
                if (autres.Count > 0) notes.Add("carte : le chargement pose aussi " + string.Join(", ", autres));
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
        // Un double-clic sur le siège lu descend comme « Entrer », une seule fois ; rien d'autre ne descend.
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
        [TestCase("entrer")] [TestCase("double-clic")]
        public void ParDefautLePassagePrendLaTransition(string cas)
        {
            string scene = TerresAvecKit.Scenes[Zab]; double t = 1;
            Servir(Zab); Servir(); Poser(); passage.ChargerScene = null;
            if (cas == "entrer") { Pas(ref t, 2); Assert.IsTrue(passage.Entrer(scene, SiegeDuZab), "Entrer ne descend pas"); }
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
