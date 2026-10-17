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
    }
}
