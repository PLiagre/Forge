using System;
using Forge.Pont;
using NUnit.Framework;

namespace Forge.Interface.Tests
{
    public sealed class DossierVoisinsTests
    {
        const string Maisons = "{\"tick\":60,\"nombre\":1,\"maisons\":[{\"id\":\"grande-10\",\"nom\":\"Maison témoin\"}]}";
        const string Geste = "{\"tick\":25,\"intention\":{\"type\":\"tracer_route\",\"maison\":\"grande-10\",\"cell\":10466},\"raison\":{\"regle\":\"route_si_bourg_affame\",\"bourg\":{\"population\":21,\"duree_faim_ticks\":1,\"dette_alimentaire_kg\":14.5,\"nourriture_kg\":0.4}}}";
        static DocumentDuMonde Document(string gestes, int compte = 1) => new DocumentDuMonde("{\"tick\":60,\"date\":{\"annee\":1400,\"jour_de_l_annee\":61},\"maisons_actives_30j\":" + compte + ",\"releve\":[" + gestes + "]}");
        static readonly Func<long, string> Bourg = c => c == 10466 ? "Milan" : throw new ArgumentException("terre inattendue : " + c);
        [Test] public void Le_journal_lit_la_maison_la_raison_et_le_recu_sans_inventer_un_effet()
        {
            string texte = DossierVoisins.Decrire(Document(Geste), new DocumentDuMonde(Maisons), Bourg);
            foreach (string attendu in new[] { "Maison témoin", "Maison témoin · il y a 35 jours", "Tracer une route à Milan", "14,5 kg", "0,4 kg", "Ordre reçu", "Activité des premiers 30 jours : 1 maison" }) StringAssert.Contains(attendu, texte);
            string refuse = Geste.Insert(Geste.Length - 1, ",\"refus\":\"terrain interdit\"");
            StringAssert.Contains("Refus : terrain interdit", DossierVoisins.Decrire(Document(refuse), new DocumentDuMonde(Maisons), Bourg));
        }
        [Test] public void Les_doublons_et_les_gestes_du_futur_sont_refuses()
        {
            var noms = new DocumentDuMonde(Maisons);
            Assert.Throws<ArgumentException>(() => DossierVoisins.Decrire(Document(Geste + "," + Geste), noms, Bourg));
            Assert.Throws<ArgumentException>(() => DossierVoisins.Decrire(Document(Geste.Replace("25", "61")), noms, Bourg));
            Assert.Throws<ArgumentException>(() => DossierVoisins.Decrire(Document(Geste.Replace("\"raison\"", "\"autre\"")), noms, Bourg));
        }
        [Test] public void Un_releve_vide_et_une_mesure_inachevee_restent_explicites()
        {
            string texte = DossierVoisins.Decrire(Document("", -1), new DocumentDuMonde(Maisons), Bourg);
            StringAssert.Contains("Aucun ordre transmis", texte);
            StringAssert.Contains("mesure en cours", texte);
        }
        [Test] public void Les_ordres_de_grenier_et_de_part_se_lisent_sans_terre()
        {
            const string Grenier = "{\"tick\":60,\"intention\":{\"type\":\"ouvrir_grenier\",\"maison\":\"grande-10\",\"kg\":1200},\"raison\":{\"regle\":\"secours_apres_faim\"}}";
            const string Part = "{\"tick\":59,\"intention\":{\"type\":\"fixer_part\",\"maison\":\"grande-10\",\"part\":0.08},\"raison\":{\"regle\":\"part_sur_projets_et_gens\"}}";
            var noms = new DocumentDuMonde(Maisons);
            string texte = null;
            Assert.DoesNotThrow(() => texte = DossierVoisins.Decrire(Document(Geste + "," + Grenier + "," + Part), noms, Bourg));
            Assert.AreEqual("Journal du jour 61 de 1400", texte.Split('\n')[0]);
            foreach (string attendu in new[] { "Maison témoin · ce jour", "Maison témoin · il y a 1 jour", "Maison témoin · il y a 35 jours",
                "Tracer une route à Milan", "Bourg affamé : 21 habitants, 1 jour de faim." }) StringAssert.Contains(attendu, texte);
            Assert.AreEqual(3, texte.Split(new[] { "Ordre non interprété par cette vue" }, StringSplitOptions.None).Length);
            Assert.IsNull(TexteDuMonde.Interdit(texte, "10466"));
            Assert.IsNull(TexteDuMonde.SansUnite(texte));
            var sansDate = new DocumentDuMonde("{\"tick\":60,\"maisons_actives_30j\":1,\"releve\":[" + Geste + "]}");
            StringAssert.Contains("Date", Assert.Throws<ArgumentException>(() => DossierVoisins.Decrire(sansDate, noms, Bourg)).Message);
            Assert.AreEqual("Journal indisponible : déclaré absent par le monde", DossierVoisins.Indisponible("Champ absent : cell 10466"));
        }
    }
}
