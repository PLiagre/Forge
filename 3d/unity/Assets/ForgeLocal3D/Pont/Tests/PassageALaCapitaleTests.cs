using System;
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
    }
}
