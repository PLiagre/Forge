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
    }
}
