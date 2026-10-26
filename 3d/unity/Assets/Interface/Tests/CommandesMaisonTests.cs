using System;
using System.Linq;
using System.Threading.Tasks;
using Forge.Pont;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface.Tests
{
    public sealed class CommandesMaisonTests
    {
        const string Document = "{\"tick\":9,\"id\":\"bar\",\"part\":0.2,\"grenier\":{\"grain\":12},\"absents\":{}}";
        [Test] public void Le_releve_garde_tick_unites_et_raison_d_absence()
        {
            string texte = CommandesMaison.Decrire(new DocumentDuMonde(Document));
            StringAssert.Contains("20 %", texte); StringAssert.Contains("tick 9", texte); StringAssert.Contains("12 kg", texte);
            string absent = Document.Replace("0.2", "null").Replace("\"absents\":{}", "\"absents\":{\"part\":\"non transmise\"}");
            StringAssert.Contains("non transmise", CommandesMaison.Decrire(new DocumentDuMonde(absent)));
            Assert.Throws<ArgumentException>(() => CommandesMaison.Decrire(new DocumentDuMonde(Document.Replace("0.2", "null"))));
        }
        [Test] public async Task Le_formulaire_attend_les_comptes_et_ne_depose_qu_apres_confirmation()
        {
            var parent = new GameObject("preuve", typeof(RectTransform));
            try
            {
                var lecture = new LectureDossier(_ => Task.FromResult(new DocumentDuMonde(Document)));
                int envois = 0;
                var ordre = new OrdreConfirme(_ => { envois++; return Task.FromResult(RecuIntention.AccepteeAu(9)); });
                var vue = parent.AddComponent<CommandesMaison>();
                vue.Initialiser(parent.transform, () => "bar", lecture, ordre);
                Button B(string nom) => parent.GetComponentsInChildren<Button>(true).Single(b => b.name == nom);
                Assert.IsFalse(B("Prélèvement").interactable);
                await lecture.Actualiser("/maison?id=bar"); vue.Afficher();
                Assert.IsTrue(B("Prélèvement").interactable);
                B("Prélèvement").onClick.Invoke(); vue.Afficher();
                parent.GetComponentInChildren<InputField>().text = "25,5";
                B("Préparer").onClick.Invoke(); vue.Afficher();
                Assert.AreEqual(0, envois); StringAssert.Contains("0.255", ordre.Brouillon);
                B("Confirmer l’ordre").onClick.Invoke(); B("Confirmer l’ordre").onClick.Invoke(); vue.Afficher();
                Assert.AreEqual(1, envois);
                Assert.IsFalse(B("Confirmer l’ordre").gameObject.activeSelf);
                Assert.IsTrue(parent.GetComponentsInChildren<Text>().Any(t => t.text.Contains("20 %")));
            }
            finally { UnityEngine.Object.DestroyImmediate(parent); }
        }
        static Button B(GameObject p, string n) => p.GetComponentsInChildren<Button>(true).Single(b => b.name == n);
        static string Textes(GameObject p) => string.Join("\n", p.GetComponentsInChildren<Text>(true).Select(t => t.text));
        static async Task<GameObject> Monter(Func<string, Task<RecuIntention>> envoyer, CommandesMaison[] vue, bool comptes)
        {
            var parent = new GameObject("preuve-656", typeof(RectTransform)); var lecture = new LectureDossier(_ => Task.FromResult(new DocumentDuMonde(Document)));
            vue[0] = parent.AddComponent<CommandesMaison>(); vue[0].Initialiser(parent.transform, () => "bar", lecture, new OrdreConfirme(envoyer));
            if (comptes) await lecture.Actualiser("/maison?id=bar"); vue[0].Afficher(); return parent;
        }
        static void Geste(GameObject p, CommandesMaison v, string bouton, string texte)
        { B(p, bouton).onClick.Invoke(); v.Afficher(); p.GetComponentInChildren<InputField>(true).text = texte; B(p, "Préparer").onClick.Invoke(); B(p, "Confirmer l’ordre").onClick.Invoke(); v.Afficher(); }
        [Test] public async Task Le_curseur_regle_chaque_point_et_n_envoie_qu_a_la_confirmation()
        {
            var envoyes = new System.Collections.Generic.List<string>(); var vue = new CommandesMaison[1];
            var parent = await Monter(json => { envoyes.Add(json); return Task.FromResult(RecuIntention.AccepteeAu(9)); }, vue, true);
            try
            {
                B(parent, "Prélèvement").onClick.Invoke(); vue[0].Afficher();
                var curseur = parent.GetComponentInChildren<Slider>(true); var saisie = parent.GetComponentInChildren<InputField>(true);
                Assert.IsNotNull(curseur, "curseur absent"); Assert.AreEqual(Slider.Direction.LeftToRight, curseur.direction);
                Assert.AreEqual(0f, curseur.minValue); Assert.AreEqual(60f, curseur.maxValue); Assert.IsTrue(curseur.wholeNumbers);
                Assert.IsNotNull(curseur.handleRect); Assert.Greater(curseur.handleRect.sizeDelta.x, 0f); Assert.IsTrue(curseur.handleRect.GetComponent<Image>().raycastTarget);
                Assert.AreEqual(20f, curseur.value, 1e-4f); Assert.AreEqual(0, envoyes.Count, "ouverture");
                for (int p = 0; p <= 60; p++)
                {
                    if (p != 0) { B(parent, "Annuler / Retour").onClick.Invoke(); vue[0].Afficher(); B(parent, "Prélèvement").onClick.Invoke(); vue[0].Afficher(); }
                    int n = envoyes.Count; curseur.value = p; vue[0].Afficher(); Assert.AreEqual(n, envoyes.Count, "déplacement " + p); Assert.AreEqual(p.ToString(), saisie.text);
                    B(parent, "Préparer").onClick.Invoke(); vue[0].Afficher(); Assert.AreEqual(n, envoyes.Count, "préparation " + p);
                    B(parent, "Confirmer l’ordre").onClick.Invoke(); vue[0].Afficher(); Assert.AreEqual(n + 1, envoyes.Count, "confirmation " + p);
                    var objet = LecteurJson.LireObjet(envoyes[n]); Assert.AreEqual(3, objet.Count, envoyes[n]); Assert.AreEqual("fixer_part", objet["type"]); Assert.AreEqual("bar", objet["maison"]); Assert.AreEqual(p / 100.0, (double)objet["part"], 1e-7, envoyes[n]);
                }
            }
            finally { UnityEngine.Object.DestroyImmediate(parent); }
        }
        [Test] public async Task Le_grenier_depasse_le_stock_et_aucune_interaction_ne_redepose()
        {
            int envois = 0; var vue = new CommandesMaison[1];
            var sans = await Monter(_ => { envois++; return Task.FromResult(RecuIntention.AccepteeAu(1)); }, vue, false);
            try
            {
                var curseur = sans.GetComponentInChildren<Slider>(true);
                Assert.IsNotNull(curseur, "curseur absent"); Assert.IsFalse(curseur.gameObject.activeSelf); Assert.IsFalse(curseur.IsInteractable());
                Assert.IsFalse(B(sans, "Confirmer l’ordre").gameObject.activeSelf);
                B(sans, "Prélèvement").onClick.Invoke(); B(sans, "Confirmer l’ordre").onClick.Invoke(); curseur.value = 60; Assert.AreEqual(0, envois);
            }
            finally { UnityEngine.Object.DestroyImmediate(sans); }
            var porte = new TaskCompletionSource<RecuIntention>();
            var parent = await Monter(_ => { envois++; return porte.Task; }, vue, true);
            try
            {
                B(parent, "Ouvrir le grenier").onClick.Invoke(); vue[0].Afficher(); parent.GetComponentInChildren<InputField>(true).text = "13,5";
                B(parent, "Préparer").onClick.Invoke(); vue[0].Afficher(); Assert.AreEqual(0, envois);
                B(parent, "Confirmer l’ordre").onClick.Invoke(); B(parent, "Confirmer l’ordre").onClick.Invoke(); vue[0].Afficher();
                Assert.AreEqual(1, envois); Assert.IsTrue(vue[0].Ordre.EnCours); Assert.IsFalse(parent.GetComponentsInChildren<Selectable>(true).Any(s => s.IsActive() && s.IsInteractable()));
                var objet = LecteurJson.LireObjet(vue[0].Ordre.Brouillon); Assert.AreEqual(3, objet.Count); Assert.AreEqual("ouvrir_grenier", objet["type"]); Assert.AreEqual("bar", objet["maison"]); Assert.AreEqual(13.5, (double)objet["kg"], 1e-7); Assert.IsFalse(objet.ContainsKey("part"));
                porte.SetResult(RecuIntention.AccepteeAu(17)); for (int i = 0; i < 30 && vue[0].Ordre.EnCours; i++) await Task.Yield();
                vue[0].Afficher(); string avant = Textes(parent); vue[0].Afficher();
                Assert.IsFalse(vue[0].Ordre.EnCours); Assert.AreEqual(17, vue[0].Ordre.Recu.AppliqueeAuTick); Assert.AreEqual(avant, Textes(parent)); Assert.AreEqual(1, envois);
                B(parent, "Annuler / Retour").onClick.Invoke(); vue[0].Afficher(); Assert.IsNull(vue[0].Ordre.Recu); Assert.AreEqual(1, envois);
            }
            finally { UnityEngine.Object.DestroyImmediate(parent); }
        }
        [Test] public async Task Le_panneau_dit_le_tick_recu_la_raison_ou_la_cause()
        {
            int etape = 0; var vue = new CommandesMaison[1]; const string Raison = "grenier insuffisant : 13.5 kg demandés, 12.0 kg disponibles";
            var parent = await Monter(_ => { etape++; return Task.FromResult(etape == 1 ? RecuIntention.AccepteeAu(17) : etape == 2 ? RecuIntention.Refusee(400, Raison) : RecuIntention.Absente("coupure témoin")); }, vue, true);
            try
            {
                Geste(parent, vue[0], "Prélèvement", "25"); string textes = Textes(parent); StringAssert.Contains("après le tick 17", textes); StringAssert.DoesNotContain("après le tick 9", textes); StringAssert.DoesNotContain("après le tick 18", textes);
                string releve = parent.GetComponentsInChildren<Text>(true).Select(t => t.text).Single(t => t.StartsWith("Prélèvement :")); StringAssert.Contains("20 %", releve); StringAssert.Contains("12 kg", releve); StringAssert.Contains("tick 9", releve);
                B(parent, "Annuler / Retour").onClick.Invoke(); vue[0].Afficher(); Geste(parent, vue[0], "Ouvrir le grenier", "13,5");
                StringAssert.Contains("Refus : " + Raison, Textes(parent));
                B(parent, "Annuler / Retour").onClick.Invoke(); vue[0].Afficher(); Geste(parent, vue[0], "Ouvrir le grenier", "1");
                textes = Textes(parent); StringAssert.Contains("Envoi non confirmé : coupure témoin", textes); StringAssert.DoesNotContain("Refus", textes);
            }
            finally { UnityEngine.Object.DestroyImmediate(parent); }
        }
    }
}
