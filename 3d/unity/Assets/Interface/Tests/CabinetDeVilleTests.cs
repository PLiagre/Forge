using System;
using System.Collections.Generic;
using System.Reflection;
using Forge.Pont;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.UI;
using Object = UnityEngine.Object;

namespace Forge.Interface.Tests
{
    public sealed class CabinetDeVilleTests
    {
        const long CELLULE = 1175;
        readonly List<Object> objets = new List<Object>();
        [TearDown] public void Fermer() { foreach (var o in objets) if (o != null) Object.DestroyImmediate(o); objets.Clear(); }

        static Lieu Servi(long hunger = 12, double deficit = 2500.25, IEnumerable<LieuPlace> lieux = null,
            EtatFoyers etat = EtatFoyers.Servis, Logement logement = null, bool sansLogement = false)
        {
            var stocks = new Dictionary<string, double> { ["nourriture"] = 123456.789012, ["bois"] = 4321.5 };
            var foyers = etat == EtatFoyers.Servis ? new Dictionary<string, (long Foyers, long Personnes)> {
                ["paysans"] = (40, 180), ["ouvriers"] = (5, 12), ["artisans"] = (1, 3) } : null;
            return new Lieu(CELLULE, 30, 1400, 31, 1234, stocks, hunger, deficit, etat, foyers,
                sansLogement ? null : logement ?? new Logement(10, 8, 2),
                lieux ?? new[] { new LieuPlace(1, null, "zab", nom: "Un hameau"), new LieuPlace(0, null, "zab", nom: "Biskra") });
        }

        static void Juge(string texte)
        {
            Assert.That(TexteDuMonde.Interdit(texte, CELLULE.ToString()), Is.Null, texte);
            Assert.That(TexteDuMonde.SansUnite(texte), Is.Null, texte);
        }

        [Test] public void LeBourgSeLitSansIdentifiantNiNombreNu()
        {
            string texte = CabinetDeVille.Decrire(Servi());
            Juge(texte);
            Assert.That(texte, Does.StartWith("Biskra · jour 31 de 1400\n"));
            Assert.That(texte, Does.Contain("Habitants : " + TexteDuMonde.Nombre(1234) + " habitants"));
            Assert.That(texte, Does.Contain("Nourriture : 123 t\n"));
            Assert.That(texte, Does.Contain("bois : 4,32 t\n"));
            Assert.That(texte, Does.Contain("Faim : 12 jours de manque"));
            Assert.That(texte, Does.Contain("Dette de nourriture : 2,50 t"));
            Assert.That(texte, Does.Contain("paysans : 40 foyers, 180 personnes"));
            Assert.That(texte, Does.Contain("artisans : 1 foyer, 3 personnes"));
            Assert.That(texte, Does.Contain("Au chantier : 12 bras pris aux champs"));
            Assert.That(texte, Does.Contain("Logement des artisans : 8 foyers logés, 2 foyers sans logis, capacité de 10 foyers"));
            Assert.That(texte, Does.Not.Contain("123456").And.Not.Contain("tick"));
        }

        [Test] public void LAncienPanneauEchoueAuMemeJuge()
        {
            var ancienne = typeof(PanneauLieu).GetMethod("Decrire", BindingFlags.NonPublic | BindingFlags.Static);
            Assert.That(ancienne, Is.Not.Null, "PanneauLieu.Decrire a changé de nom : la contre-épreuve ne juge plus rien");
            string ancien = (string)ancienne.Invoke(null, new object[] { Servi() });
            Assert.That(ancien, Does.Contain("Cellule 1175 · tick 30"));
            Assert.That(TexteDuMonde.Interdit(ancien, CELLULE.ToString()), Is.Not.Null, ancien);
            Assert.That(TexteDuMonde.SansUnite(ancien), Is.Not.Null, ancien);
        }

        [Test] public void LaFaimSeLitEnJoursDeManque()
        {
            string aucune = CabinetDeVille.Decrire(Servi(hunger: 0));
            Assert.That(aucune, Does.Contain("Faim : aucune"));
            Assert.That(aucune, Does.Not.Contain("manque"));
            Assert.That(CabinetDeVille.Decrire(Servi(hunger: 1)), Does.Contain("Faim : 1 jour de manque"));
            string longue = CabinetDeVille.Decrire(Servi(hunger: 1500));
            Assert.That(longue, Does.Contain("Faim : " + TexteDuMonde.Jours(1500) + " de manque"));
            Juge(longue);
            string inconnue = CabinetDeVille.Decrire(Servi(hunger: -1, deficit: -1));
            Assert.That(inconnue, Does.Contain("Faim : non calculée").And.Contain("Dette de nourriture : non calculée"));
            Assert.That(inconnue, Does.Not.Contain("-1"));
            Juge(inconnue);
        }

        [Test] public void UnLieuSansBourgNommeNeDevinePasSonNom()
        {
            string sans = CabinetDeVille.Decrire(Servi(lieux: new[] { new LieuPlace(1, null, "zab", nom: "Un hameau") }));
            Assert.That(sans, Does.StartWith("Bourg sans nom · jour 31 de 1400\n").And.Not.Contain("hameau"));
            Juge(sans);
            Assert.That(CabinetDeVille.Decrire(Servi(lieux: new LieuPlace[0])), Does.StartWith("Bourg sans nom"));
            Juge(CabinetDeVille.Decrire(new Lieu(CELLULE, 30, 1400, 31, 1, new Dictionary<string, double>(), 0, 0)));
        }

        [Test] public void LesFoyersEtLeLogementNonServisSeDisentSansChiffre()
        {
            string absents = CabinetDeVille.Decrire(Servi(etat: EtatFoyers.Absents, sansLogement: true));
            Assert.That(absents, Does.Contain("Foyers par métier : absents de la réponse du service").And.Contain("Au chantier : absent de la réponse du service")
                .And.Contain("Logement : absent du service"));
            Juge(absents);
            string inconnus = CabinetDeVille.Decrire(Servi(etat: EtatFoyers.NonCalcules, logement: new Logement(10, -1, -1)));
            Assert.That(inconnus, Does.Contain("non calculés par le monde").And.Contain("Au chantier : non calculé")
                .And.Contain("capacité de 10 foyers, logés et sans-logis non calculés"));
            Juge(inconnus);
        }

        [Test] public void UnLieuAbsentDeStocksSeDitAbsentDuGrenier()
        {
            var vide = new Lieu(CELLULE, 30, 1400, 31, 0, new Dictionary<string, double>(), 0, 0);
            string texte = CabinetDeVille.Decrire(vide);
            Assert.That(texte, Does.Contain("Nourriture : absente du grenier").And.Contain("Habitants : 0 habitant"));
            Juge(texte);
        }

        [Test] public void LaToileSeDessinePourLaCameraEtAttendLeMonde()
        {
            var camera = UneCamera();
            var cabinet = Poser(camera, null, null);
            var toile = cabinet.Toile;
            Assert.That(toile.renderMode, Is.EqualTo(RenderMode.ScreenSpaceCamera));
            Assert.That(toile.worldCamera, Is.SameAs(camera));
            Assert.That(toile.planeDistance, Is.GreaterThan(camera.nearClipPlane));
            var echelle = toile.GetComponent<CanvasScaler>();
            Assert.That(echelle.referenceResolution, Is.EqualTo(new Vector2(1920, 1080)));
            Assert.That(cabinet.TexteDuBourg, Does.StartWith("… En attente").And.Contain(CabinetDeVille.ATTENTE));
            Assert.That(TexteDuMonde.SansUnite(cabinet.TexteDuBourg), Is.Null);
            foreach (var feuillet in new[] { cabinet.FeuilletDuBourg, cabinet.FeuilletDesOutils })
            {
                Assert.That(feuillet.Find("Filet"), Is.Not.Null, feuillet.name + " ne vient pas du socle");
                Assert.That(feuillet.GetComponent<Shadow>(), Is.Not.Null, feuillet.name);
                Assert.That(feuillet.IsChildOf(toile.transform), Is.True, feuillet.name);
            }
            Assert.That(cabinet.FeuilletDuBourg.name, Is.EqualTo(CabinetDeVille.BOURG));
            Assert.That(cabinet.FeuilletDesOutils.name, Is.EqualTo(CabinetDeVille.OUTILS));
        }

        [Test] public void LesOutilsSeLisentDansLeurFeuilletEtSansEuxIlsSeCachent()
        {
            string aide = "Clic : poser un point · Entrée : tracer la route";
            var cabinet = Poser(UneCamera(), null, () => aide);
            Assert.That(cabinet.FeuilletDesOutils.gameObject.activeSelf, Is.True);
            Assert.That(cabinet.TexteDesOutils, Is.EqualTo(aide));
            aide = "";
            UneImage(cabinet);
            Assert.That(cabinet.FeuilletDesOutils.gameObject.activeSelf, Is.False);
            aide = "Echap : annuler";
            UneImage(cabinet);
            Assert.That(cabinet.FeuilletDesOutils.gameObject.activeSelf, Is.True);
            Assert.That(cabinet.TexteDesOutils, Is.EqualTo(aide));
            Assert.That(cabinet.FeuilletDesOutils.anchorMin, Is.EqualTo(Vector2.zero), "les outils s'ancrent en bas à gauche");
        }

        Camera UneCamera()
        {
            var objet = new GameObject("Caméra de contrôle", typeof(Camera));
            objets.Add(objet);
            return objet.GetComponent<Camera>();
        }

        CabinetDeVille Poser(Camera camera, PanneauLieu lieu, Func<string> outils)
        {
            var racine = new GameObject("Ville de contrôle");
            objets.Add(racine);
            var cabinet = racine.AddComponent<CabinetDeVille>();
            cabinet.Initialiser(camera, lieu, outils);
            return cabinet;
        }

        // Une image du cabinet : LateUpdate relit le panneau du lieu et l'outil.
        static void UneImage(CabinetDeVille cabinet) =>
            typeof(CabinetDeVille).GetMethod("LateUpdate", BindingFlags.NonPublic | BindingFlags.Instance).Invoke(cabinet, null);
    }
}
