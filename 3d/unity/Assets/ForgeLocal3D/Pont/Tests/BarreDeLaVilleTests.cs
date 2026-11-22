using System;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.UI;
using Object = UnityEngine.Object;

namespace Forge.Pont.Tests
{
    // La barre des outils de la ville, montée sur une toile par une fabrique de test : chaque geste de la ville a son bouton,
    // qui porte son nom et son raccourci et joue son geste ; l'état composé se montre tel quel.
    public sealed class BarreDeLaVilleTests
    {
        // Les gestes que la fiche demande en boutons, écrits ici et non relus du code : un geste retiré de la table fait échouer.
        static readonly (string nom, string touche, GesteDeLaVille geste)[] GestesDeLaFiche =
        {
            ("Rue", "R", GesteDeLaVille.Rue), ("Parcelle", "P", GesteDeLaVille.Parcelle), ("Caserne", "4", GesteDeLaVille.Caserne),
            ("Valider", "Entrée", GesteDeLaVille.Valider), ("Annuler", "Échap", GesteDeLaVille.Annuler), ("Retour à la carte", "C", GesteDeLaVille.Retour),
        };
        static readonly Color Presse = new Color(.1f, .2f, .3f, 1f);

        GameObject toile; readonly List<GesteDeLaVille> joues = new();
        [SetUp] public void Monter() { toile = new GameObject("Toile du test", typeof(RectTransform), typeof(Canvas)); joues.Clear(); }
        [TearDown] public void Demonter() { if (toile) Object.DestroyImmediate(toile); }

        static Text Texte(Transform parent)
        {
            var t = new GameObject("Texte", typeof(RectTransform)).AddComponent<Text>(); t.transform.SetParent(parent, false);
            t.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf"); return t;
        }
        static readonly FabriqueDeLaBarre Fabrique = new FabriqueDeLaBarre(
            (parent, nom, action) =>
            {
                var o = new GameObject(nom, typeof(RectTransform), typeof(Image), typeof(Button)); o.transform.SetParent(parent, false);
                var b = o.GetComponent<Button>(); var c = b.colors; c.pressedColor = Presse; b.colors = c;
                b.onClick.AddListener(() => action()); Texte(o.transform).text = nom; return b;
            },
            Texte,
            (parent, titre, largeur, hauteur) =>
            {
                var r = new GameObject(titre, typeof(RectTransform)).GetComponent<RectTransform>(); r.SetParent(parent, false); r.sizeDelta = new Vector2(largeur, hauteur); return r;
            },
            actif => actif ? Clair : Sombre);
        static readonly Color Clair = new Color(.9f, .9f, .8f, 1f), Sombre = new Color(.1f, .1f, .1f, 1f);

        BarreDeLaVille Monter(EtatDesOutils etat)
        {
            var gestes = Enum.GetValues(typeof(GesteDeLaVille)).Cast<GesteDeLaVille>().ToDictionary(g => g, g => (Action)(() => joues.Add(g)));
            var barre = new BarreDeLaVille(toile.transform, Fabrique, gestes);
            barre.Appliquer(OutilsDeLaVille.Composer(etat));
            return barre;
        }
        static BatimentDeLevee Devis(double manque = 0) => new BatimentDeLevee("caserne", "Caserne", 10465, 800, 25, 2400, manque, manque > 0 ? "grenier insuffisant : 2400 kg" : null);

        // La preuve de la fiche : sans bouton pour un geste de la ville, ou un bouton qui ne le joue pas, le test échoue.
        [Test] public void Chaque_geste_de_la_ville_a_un_bouton_qui_porte_son_raccourci_et_le_joue()
        {
            Monter(new EtatDesOutils { Outil = OutilDeLaVille.Rue, Points = 2, Devis = Devis() });
            var tous = toile.GetComponentsInChildren<Button>(true);
            foreach (var (nom, touche, geste) in GestesDeLaFiche)
            {
                var siens = tous.Where(b => b.GetComponentInChildren<Text>(true).text.StartsWith(nom + " (" + touche + ")", StringComparison.Ordinal)).ToArray();
                Assert.AreEqual(1, siens.Length, "le geste « " + nom + " » n'a pas son bouton « " + nom + " (" + touche + ") »");
                Assert.IsTrue(siens[0].gameObject.activeInHierarchy && siens[0].interactable, nom + " : bouton caché ou grisé, outil Rue en main avec deux points");
                joues.Clear(); siens[0].onClick.Invoke();
                CollectionAssert.AreEqual(new[] { geste }, joues, nom + " : le bouton ne joue pas son geste");
            }
        }

        [Test] public void Sans_outil_valider_et_annuler_se_cachent_et_la_ligne_le_dit()
        {
            var barre = Monter(new EtatDesOutils { Devis = Devis() });
            Assert.IsFalse(barre.Bouton(GesteDeLaVille.Valider).gameObject.activeSelf); Assert.IsFalse(barre.Bouton(GesteDeLaVille.Annuler).gameObject.activeSelf);
            Assert.IsTrue(barre.Bouton(GesteDeLaVille.Retour).gameObject.activeSelf);
            Assert.AreEqual(OutilsDeLaVille.SANS_OUTIL, barre.Ligne.text);
            Assert.AreEqual(BarreDeLaVille.TITRE, barre.Panneau.name);
            // Le retour est en haut de la toile ; la barre en bas.
            Assert.AreEqual(1f, ((RectTransform)barre.Bouton(GesteDeLaVille.Retour).transform).anchorMin.y); Assert.AreEqual(0f, barre.Panneau.anchorMin.y);
        }

        [Test] public void L_outil_en_main_prend_la_couleur_pressee_de_son_bouton_et_la_rend()
        {
            var barre = Monter(new EtatDesOutils { Outil = OutilDeLaVille.Parcelle, Devis = Devis() });
            Assert.AreEqual(Presse, barre.Bouton(GesteDeLaVille.Parcelle).colors.normalColor);
            Assert.AreNotEqual(Presse, barre.Bouton(GesteDeLaVille.Rue).colors.normalColor);
            barre.Appliquer(OutilsDeLaVille.Composer(new EtatDesOutils { Outil = OutilDeLaVille.Rue, Devis = Devis() }));
            Assert.AreEqual(Presse, barre.Bouton(GesteDeLaVille.Rue).colors.normalColor);
            Assert.AreNotEqual(Presse, barre.Bouton(GesteDeLaVille.Parcelle).colors.normalColor);
            Assert.AreEqual(Color.white, barre.Bouton(GesteDeLaVille.Parcelle).colors.normalColor, "la couleur de repos du bouton n'est pas rendue");
        }

        [Test] public void La_caserne_grisee_dit_son_manque_sur_son_bouton()
        {
            var barre = Monter(new EtatDesOutils { Devis = Devis(615.5) });
            var b = barre.Bouton(GesteDeLaVille.Caserne);
            Assert.IsFalse(b.interactable); Assert.AreEqual("Caserne (4)\nil manque 615,5 kg de grain", b.GetComponentInChildren<Text>(true).text);
            Assert.AreEqual(Sombre, b.GetComponentInChildren<Text>(true).color, "le libellé grisé prend l'encre que la fabrique donne au bouton grisé");
            barre.Appliquer(OutilsDeLaVille.Composer(new EtatDesOutils { Devis = Devis() }));
            Assert.IsTrue(b.interactable); Assert.AreEqual("Caserne (4)\n2,40 t de grain", b.GetComponentInChildren<Text>(true).text);
            Assert.AreEqual(Clair, b.GetComponentInChildren<Text>(true).color);
        }

        [Test] public void Les_boutons_visibles_se_rangent_sans_trou()
        {
            var barre = Monter(new EtatDesOutils { Outil = OutilDeLaVille.Rue, Points = 2, Devis = Devis() });
            float X(GesteDeLaVille g) => ((RectTransform)barre.Bouton(g).transform).anchoredPosition.x;
            var rangee = new[] { GesteDeLaVille.Rue, GesteDeLaVille.Parcelle, GesteDeLaVille.Caserne, GesteDeLaVille.Valider, GesteDeLaVille.Annuler }.Select(X).ToArray();
            for (int i = 1; i < rangee.Length; i++) Assert.Greater(rangee[i], rangee[i - 1]);
            // L'outil Caserne n'a pas de Valider : Annuler prend sa place.
            float valider = X(GesteDeLaVille.Valider);
            barre.Appliquer(OutilsDeLaVille.Composer(new EtatDesOutils { Outil = OutilDeLaVille.Caserne, Devis = Devis() }));
            Assert.IsFalse(barre.Bouton(GesteDeLaVille.Valider).gameObject.activeSelf); Assert.AreEqual(valider, X(GesteDeLaVille.Annuler));
        }

        [Test] public void Un_geste_sans_action_est_refuse()
        {
            var gestes = Enum.GetValues(typeof(GesteDeLaVille)).Cast<GesteDeLaVille>().Where(g => g != GesteDeLaVille.Retour).ToDictionary(g => g, g => (Action)(() => { }));
            var e = Assert.Throws<ArgumentException>(() => new BarreDeLaVille(toile.transform, Fabrique, gestes));
            StringAssert.Contains("Retour à la carte", e.Message);
        }
    }
}
