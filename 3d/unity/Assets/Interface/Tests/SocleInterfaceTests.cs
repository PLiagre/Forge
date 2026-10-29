using System;
using System.Collections;
using System.Linq;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using UnityEngine.TestTools;
using UnityEditor.TestTools;

namespace Forge.Interface.Tests
{
    public sealed class SocleInterfaceTests
    {
        GameObject galerie;
        EventSystem evenements;

        [SetUp] public void Ouvrir()
        {
            galerie = SocleInterface.Creer();
            evenements = galerie.GetComponentInChildren<EventSystem>();
        }

        [TearDown] public void Fermer() => UnityEngine.Object.DestroyImmediate(galerie);

        [UnityTest] public IEnumerator LaSceneReconstruitSesCommandesEnPlay()
        {
            UnityEngine.Object.DestroyImmediate(galerie);
            yield return new EnterPlayMode();
            galerie = new GameObject("Scène du socle", typeof(SocleInterface));
            yield return null;
            evenements = galerie.GetComponentInChildren<EventSystem>();
            LeClicActifNeFermePasLeDossierVoisin();
            UnityEngine.Object.DestroyImmediate(galerie);
            yield return new ExitPlayMode();
        }

        Button Bouton(string nom)
        {
            var bouton = galerie.GetComponentsInChildren<Button>(true).SingleOrDefault(b => b.name == nom);
            Assert.That(bouton, Is.Not.Null, "bouton absent : " + nom);
            return bouton;
        }

        [Test] public void LesPolicesEmbarqueesDistinguentTitresEtLecture()
        {
            var textes = galerie.GetComponentsInChildren<Text>();
            var titre = textes.First(t => t.fontSize == SocleInterface.Titre);
            var corps = textes.First(t => t.fontSize == SocleInterface.Corps);
            Assert.That(titre.font.name, Is.EqualTo("NotoSerif-Regular"));
            Assert.That(corps.font.name, Is.EqualTo("NotoSans-Regular"));
            foreach (var police in new[] { titre.font, corps.font })
            {
                police.RequestCharactersInTexture("ÉÀÇœéèêùî0123456789", 18);
                foreach (char lettre in "ÉÀÇœéèêùî0123456789")
                    Assert.That(police.HasCharacter(lettre), Is.True, lettre.ToString());
            }
        }

        [Test] public void LeThemeRefuseUnJetonInconnu()
        {
            Assert.Throws<ArgumentException>(() => SocleInterface.Couleur("inconnue"));
            ColorUtility.TryParseHtmlString("#E8DDC9", out var papier);
            Assert.That(SocleInterface.Couleur("papier"), Is.EqualTo(papier));
        }

        [Test] public void DeuxDossiersRestentVisiblesEtLaGalerieEstDeclaree()
        {
            foreach (var nom in new[] { "Le domaine", "Le conseil" })
                Assert.That(galerie.GetComponentsInChildren<Image>().Any(p => p.name == nom), Is.True, nom);
            Assert.That(galerie.GetComponentsInChildren<Text>().Any(t => t.text.Contains("aucune partie chargée")), Is.True);
        }

        [Test] public void LeFocusReelChangeLaCouleurDuBouton()
        {
            var bouton = Bouton("Consulter le dossier");
            var normal = bouton.targetGraphic.canvasRenderer.GetColor();
            evenements.SetSelectedGameObject(bouton.gameObject);
            Assert.That(bouton.targetGraphic.canvasRenderer.GetColor(), Is.Not.EqualTo(normal));
            Assert.That(bouton.GetComponent<Outline>().enabled, Is.True);
            evenements.SetSelectedGameObject(null);
            Assert.That(bouton.GetComponent<Outline>().enabled, Is.False);
        }

        [Test] public void UnBoutonInactifNeDeclencheRien()
        {
            var bouton = Bouton("En attente du monde");
            int appels = 0;
            bouton.onClick.AddListener(() => appels++);
            ExecuteEvents.Execute(bouton.gameObject, new PointerEventData(evenements), ExecuteEvents.pointerClickHandler);
            Assert.That(bouton.interactable, Is.False);
            Assert.That(appels, Is.Zero);
        }

        [Test] public void LeClicActifNeFermePasLeDossierVoisin()
        {
            var bouton = Bouton("Consulter le dossier");
            int appels = 0;
            bouton.onClick.AddListener(() => appels++);
            ExecuteEvents.Execute(bouton.gameObject, new PointerEventData(evenements), ExecuteEvents.pointerClickHandler);
            Assert.That(appels, Is.EqualTo(1));
            Assert.That(galerie.GetComponentsInChildren<Text>().Any(t => t.text.Contains("Aucun ordre envoyé")), Is.True);
            DeuxDossiersRestentVisiblesEtLaGalerieEstDeclaree();
        }

        // Lot #878 : l'infobulle du socle, entière dans l'écran et jamais sur le point survolé.
        static readonly (string nom, string phrase)[] Phrases = { ("Consulter le dossier", "Ouvre le dossier sans rien envoyer au monde."),
            ("En attente du monde", "Indisponible : aucune partie chargée."), ("Parcourir au clavier", "Passe d'une commande à l'autre avec les flèches ; Entrée agit.") };
        const float ARRONDI = 1e-3f; // l'arrondi flottant, en pixels
        Canvas Toile => galerie.GetComponentsInChildren<Canvas>(true).Single(c => c.name == "Documents");
        static Rect Carre(Vector2 p) => new Rect(p.x - 24, p.y - 24, 48, 48);
        static bool Chevauche(Rect r, Vector2 p) => Rect.MinMaxRect(r.xMin + ARRONDI, r.yMin + ARRONDI, r.xMax - ARRONDI, r.yMax - ARRONDI).Overlaps(Carre(p));
        static bool Dedans(Rect r, Rect ecran) => r.xMin >= ecran.xMin - ARRONDI && r.yMin >= ecran.yMin - ARRONDI && r.xMax <= ecran.xMax + ARRONDI && r.yMax <= ecran.yMax + ARRONDI;

        [Test] public void LInfobulleResteEntiereEtLibereLePoint()
        {
            string longue = Phrases.Select(p => p.phrase).OrderByDescending(p => p.Length).First();
            Vector2 unites = Infobulle.Montrer(Toile, longue, Toile.pixelRect.position).rect.size;
            Assert.That(unites.x, Is.GreaterThan(0)); Assert.That(unites.y, Is.GreaterThan(0));
            int juges = 0;
            foreach (var ecran in new[] { new Vector2(1920, 1080), new Vector2(1280, 720) })
            {
                Vector2 taille = unites * (ecran.x / 1920);
                for (int i = 0; i <= ecran.x / 20; i++)
                    for (int j = 0; j <= ecran.y / 20; j++, juges++)
                    {
                        var p = new Vector2(i * 20, j * 20); Rect r = Infobulle.Placer(p, taille, ecran);
                        if (!Dedans(r, new Rect(Vector2.zero, ecran)) || Chevauche(r, p)) Assert.Fail("écran " + ecran + ", point " + p + " : feuillet " + r);
                    }
                Assert.Throws<ArgumentException>(() => Infobulle.Placer(ecran / 2, new Vector2(ecran.x / 2, taille.y), ecran));
                Assert.Throws<ArgumentException>(() => Infobulle.Placer(ecran / 2, new Vector2(taille.x, ecran.y / 2), ecran));
            }
            Assert.That(juges, Is.EqualTo(97 * 55 + 65 * 37), "points jugés");
        }

        [Test] public void UneCommandeRefuseUnePhraseVide()
        {
            Transform domaine = galerie.GetComponentsInChildren<Image>().Single(i => i.name == "Le domaine").transform;
            foreach (var p in new[] { "", "   ", "\n" })
            {
                var refus = Assert.Throws<ArgumentException>(() => SocleInterface.Commande(domaine, "Commande sans phrase", 24, 540, null, true, p));
                StringAssert.Contains("Commande sans phrase", refus.Message);
                Assert.That(domaine.Cast<Transform>().Count(t => t.name == "Commande sans phrase"), Is.Zero, "enfant laissé par « " + p + " »");
            }
            Assert.Throws<ArgumentException>(() => Infobulle.Montrer(Toile, "", Toile.pixelRect.center));
            Assert.That(SocleInterface.Commande(domaine, "Sans phrase", 24, 540, null).GetComponent<Infobulle>(), Is.Null);
            Assert.That(SocleInterface.Commande(domaine, "Avec phrase", 24, 600, null, true, "Fait ceci.").GetComponent<Infobulle>().Phrase, Is.EqualTo("Fait ceci."));
        }

        [Test] public void LaGalerieMontreLInfobulleSurSesCommandes()
        {
            Canvas toile = Toile; Canvas.ForceUpdateCanvases();
            var coins = new Vector3[4];
            foreach (var (nom, phrase) in Phrases)
            {
                var bouton = Bouton(nom); ((RectTransform)bouton.transform).GetWorldCorners(coins);
                Vector2 point = RectTransformUtility.WorldToScreenPoint(null, (coins[0] + coins[2]) / 2);
                ExecuteEvents.Execute(bouton.gameObject, new PointerEventData(evenements) { position = point }, ExecuteEvents.pointerEnterHandler);
                var feuillets = toile.GetComponentsInChildren<RectTransform>().Where(t => t.name == "Infobulle").ToArray();
                Assert.That(feuillets.Length, Is.EqualTo(1), nom);
                Assert.That(feuillets[0].GetComponentInChildren<Text>().text, Is.EqualTo(phrase));
                feuillets[0].GetWorldCorners(coins);
                var ecran = coins.Select(c => RectTransformUtility.WorldToScreenPoint(null, c)).ToArray();
                Rect r = Rect.MinMaxRect(ecran.Min(e => e.x), ecran.Min(e => e.y), ecran.Max(e => e.x), ecran.Max(e => e.y));
                Assert.That(Dedans(r, toile.pixelRect), Is.True, nom + " : feuillet " + r + " hors de " + toile.pixelRect);
                Assert.That(Chevauche(r, point), Is.False, nom + " : feuillet " + r + " sur le point " + point);
                ExecuteEvents.Execute(bouton.gameObject, new PointerEventData(evenements) { position = point }, ExecuteEvents.pointerExitHandler);
                Assert.That(feuillets[0].gameObject.activeSelf, Is.False, nom);
            }
            Assert.That(galerie.GetComponentsInChildren<Canvas>(true).Length, Is.EqualTo(1));
            Assert.That(toile.transform.Find("Infobulle").GetComponentsInChildren<Graphic>(true).Where(g => g.raycastTarget), Is.Empty);
        }
    }
}
