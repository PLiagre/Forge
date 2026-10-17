using System;
using NUnit.Framework;

namespace Forge.Interface.Tests
{
    public sealed class DossierVoisinsTests
    {
        const string Maisons = "{\"tick\":60,\"nombre\":1,\"maisons\":[{\"id\":\"grande-10\",\"nom\":\"Maison témoin\"}]}";
        const string Geste = "{\"tick\":25,\"intention\":{\"type\":\"tracer_route\",\"maison\":\"grande-10\",\"cell\":10466},\"raison\":{\"regle\":\"route_si_bourg_affame\",\"bourg\":{\"population\":21,\"duree_faim_ticks\":1,\"dette_alimentaire_kg\":14.5,\"nourriture_kg\":0.4}}}";
        static DocumentDuMonde Document(string gestes, int compte = 1) => new DocumentDuMonde("{\"tick\":60,\"maisons_actives_30j\":" + compte + ",\"releve\":[" + gestes + "]}");
        [Test] public void Le_journal_lit_la_maison_la_raison_et_le_recu_sans_inventer_un_effet()
        {
            string texte = DossierVoisins.Decrire(Document(Geste), new DocumentDuMonde(Maisons));
            foreach (string attendu in new[] { "Maison témoin", "tick 25", "10466", "14,5 kg", "0,4 kg", "Ordre reçu", "30 premiers jours" }) StringAssert.Contains(attendu, texte);
            string refuse = Geste.Insert(Geste.Length - 1, ",\"refus\":\"terrain interdit\"");
            StringAssert.Contains("Refus : terrain interdit", DossierVoisins.Decrire(Document(refuse), new DocumentDuMonde(Maisons)));
        }
        [Test] public void Les_doublons_et_les_gestes_du_futur_sont_refuses()
        {
            var noms = new DocumentDuMonde(Maisons);
            Assert.Throws<ArgumentException>(() => DossierVoisins.Decrire(Document(Geste + "," + Geste), noms));
            Assert.Throws<ArgumentException>(() => DossierVoisins.Decrire(Document(Geste.Replace("25", "61")), noms));
            Assert.Throws<ArgumentException>(() => DossierVoisins.Decrire(Document(Geste.Replace("\"raison\"", "\"autre\"")), noms));
        }
        [Test] public void Un_releve_vide_et_une_mesure_inachevee_restent_explicites()
        {
            string texte = DossierVoisins.Decrire(Document("", -1), new DocumentDuMonde(Maisons));
            StringAssert.Contains("Aucun ordre transmis", texte);
            StringAssert.Contains("mesure en cours", texte);
        }
    }
}
