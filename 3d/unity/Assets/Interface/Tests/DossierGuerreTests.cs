using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Forge.Pont;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.UI;
using Object = UnityEngine.Object;

namespace Forge.Interface.Tests
{
    // Le feuillet « La guerre », branché à des lectures dictées et à un envoi dicté qui garde chaque intention déposée.
    public sealed class DossierGuerreTests
    {
        const string M = "maison-joueur", CIBLE = "plausible-10461-0", FERMEE = "la levée est fermée : aucune caserne achevée dans votre capitale";
        GameObject toile; RectTransform panneau; DossierGuerre dossier; List<string> envoyes; RecuIntention reponse; CelluleDeCarte gardee; double horloge;

        [SetUp] public void Ouvrir()
        {
            horloge = 0; envoyes = new List<string>(); reponse = RecuIntention.AccepteeAu(5); gardee = new CelluleDeCarte(10461, new PolygoneDeCarte[0], null, null, new VilleDeCarte[0]);
            toile = new GameObject("Toile témoin", typeof(Canvas)); panneau = SocleInterface.Panneau(toile.transform, "Votre maison", 1312, 124, 584, 536);
            var ordre = new OrdreConfirme(json => { envoyes.Add(json); return Task.FromResult(reponse); });
            dossier = toile.AddComponent<DossierGuerre>();
            dossier.Initialiser(toile.transform, panneau, () => M, () => gardee, ordre, new NomsDesTerres(c => LectureLieu.Absent("nom témoin absent")), 8000);
            dossier.LecteurMaison = id => Lecture<MaisonLue>.De(new MaisonLue(id, id == CIBLE ? "Seigneurs du Zab" : "Maison voisine", new SiegeDeMaison(null, null, "Siège", null), new LieuTenu[0], new Dictionary<string, string>()));
        }
        [TearDown] public void Fermer() => Object.DestroyImmediate(toile);

        static OrdresDeGuerre Devis(string refusLevee = null, string refusSiege = null, bool cible = true) => new OrdresDeGuerre(M, 5, new DateDuMonde(1400, 6),
            new LeveeLue(refusLevee, new[] { new LieuDeLevee(10465, 0, 320), new LieuDeLevee(10465, 1, 315), new LieuDeLevee(10465, 2, 0) }, 500, 17084.9, 2.5),
            cible ? new CibleLue(10461, CIBLE, null) : null,
            new[] { new OrdresDUneArmee(0, 10465, 0, 1200, 5000, null, null, cible ? new MarcheLue(null, new long[] { 10461 }, 358.69, 18) : null, refusSiege, null, 1200, 5000) });
        static GuerresLues Guerres() => new GuerresLues(12, new DateDuMonde(1400, 13), new[] { new GuerreLue(0, M, CIBLE, 2) },
            new[] { new ArmeeLue(0, M, 10465, 0, 1200, 5000, null, new LieuDuPays(10461, 0), new long[] { 10461 }, new PointCarte(0, 0), new PointCarte[0]) },
            new[] { new PriseLue(0, 10461, CIBLE, M, new long[] { 0, 1 }, 11) }, 0);

        void Servir(OrdresDeGuerre devis, GuerresLues guerres = null)
        {
            dossier.LecteurOrdres = (m, c) => Lecture<OrdresDeGuerre>.De(devis); dossier.LecteurGuerres = () => Lecture<GuerresLues>.De(guerres ?? Guerres());
            if (!dossier.Feuillet.Ouvert) Bouton(panneau, DossierGuerre.COMMANDE).onClick.Invoke();
            dossier.Pas(horloge); var fin = DateTime.UtcNow.AddSeconds(5); while (dossier.LectureEnVol && DateTime.UtcNow < fin) System.Threading.Thread.Sleep(5);
            Assert.That(dossier.LectureEnVol, Is.False, "lecture encore en vol"); dossier.Pas(horloge); horloge += DossierGuerre.PERIODE_S;
            Assert.That(dossier.EtatAffiche, Is.EqualTo("Ordres de votre maison · relevé au jour 6 de 1400"));
        }
        static Button Bouton(Transform parent, string nom) => parent.GetComponentsInChildren<Button>(true).Single(b => b.name == nom);
        void Cliquer(string nom) { dossier.Afficher(horloge); dossier.Commande(nom).onClick.Invoke(); dossier.Afficher(horloge); }
        static string Illisible(string texte) => TexteDuMonde.Interdit(texte, M, CIBLE, "10461", "10465") ?? TexteDuMonde.SansUnite(texte);

        [Test] public void Chaque_ordre_depose_l_intention_attendue()
        {
            Servir(Devis());
            Assert.That((dossier.CurseurHommes.maxValue, dossier.CurseurVivres.maxValue), Is.EqualTo((500f, 17084f)), "les curseurs ne vont pas au maximum servi");
            dossier.CurseurHommes.value = 400; dossier.CurseurVivres.value = 5000;
            Cliquer(DossierGuerre.LEVER); Assert.That(envoyes, Is.Empty, "préparer n'envoie rien"); Assert.That(dossier.MessageAffiche, Does.StartWith("Lever l'ost : 400 hommes et 5,00 t de vivres."));
            Cliquer(DossierGuerre.CONFIRMER);
            Assert.That(envoyes.Single(), Is.EqualTo("{\"type\":\"lever_armee\",\"maison\":\"maison-joueur\",\"lieux\":[[10465,0,320],[10465,1,80]],\"vivres_kg\":5000}"));
            Assert.That(dossier.MessageAffiche, Is.EqualTo("Lever l'ost : ordre reçu. Le monde l'applique au jour suivant."));
            Cliquer(DossierGuerre.RETOUR);
            var attendus = new[] {
                (DossierGuerre.DECLARER, "{\"type\":\"declarer_guerre\",\"maison\":\"maison-joueur\",\"cible\":\"plausible-10461-0\"}"),
                (DossierGuerre.MARCHER, "{\"type\":\"marcher\",\"maison\":\"maison-joueur\",\"armee\":0,\"cell\":10461,\"rang\":0}"),
                (DossierGuerre.ASSIEGER, "{\"type\":\"assieger\",\"maison\":\"maison-joueur\",\"armee\":0}"),
                (DossierGuerre.RENVOYER, "{\"type\":\"renvoyer_armee\",\"maison\":\"maison-joueur\",\"armee\":0}") };
            foreach (var (nom, json) in attendus)
            {
                Cliquer(nom); Assert.That(dossier.Ordre.Brouillon, Is.EqualTo(json), nom); Cliquer(DossierGuerre.CONFIRMER);
                Assert.That(envoyes.Last(), Is.EqualTo(json), nom); Cliquer(DossierGuerre.RETOUR);
            }
            Assert.That(envoyes, Has.Count.EqualTo(5));
            Assert.That(dossier.TexteDe(DossierGuerre.DECLARER), Does.Contain("Seigneurs du Zab"));
            foreach (var texte in new[] { dossier.TexteDe(DossierGuerre.LEVER), dossier.TexteDe(DossierGuerre.DECLARER), dossier.TexteDe("Ordres de l'armée"), dossier.TexteDe("Armée choisie"), dossier.EtatAffiche })
                Assert.That(Illisible(texte), Is.Null, texte);
            Assert.That(dossier.TexteDe("Ordres de l'armée"), Does.Contain("18 jours, 359 km"));
        }

        [Test] public void La_levee_se_repartit_dans_l_ordre_des_lieux_jusqu_a_leur_part()
        {
            var levee = Devis().Levee;
            Assert.That(IntentionsDeGuerre.Repartir(levee, 635), Is.EqualTo(new[] { (10465L, 0L, 320L), (10465L, 1L, 180L) }), "plafonnée aux paysans servis");
            Assert.That(IntentionsDeGuerre.Repartir(levee, 100), Is.EqualTo(new[] { (10465L, 0L, 100L) }));
            Assert.That(IntentionsDeGuerre.Repartir(levee, 0), Is.Empty); Assert.Throws<ArgumentException>(() => IntentionsDeGuerre.Lever(M, new (long, long, long)[0], 0));
        }

        [Test] public void Un_refus_du_monde_s_affiche_avec_sa_raison()
        {
            reponse = RecuIntention.Refusee(400, FERMEE); Servir(Devis()); dossier.CurseurHommes.value = 10;
            Cliquer(DossierGuerre.LEVER); Cliquer(DossierGuerre.CONFIRMER);
            Assert.That(dossier.MessageAffiche, Is.EqualTo("× Demande refusée\nLever l'ost : " + FERMEE));
            Assert.That(dossier.TexteDe("Message des ordres"), Is.EqualTo(dossier.MessageAffiche));
            Assert.That((Color32)toile.GetComponentsInChildren<Text>(true).Single(t => t.name == "Message des ordres").color, Is.EqualTo((Color32)SocleInterface.Couleur("alerte")));
            // Une raison qui montrerait un identifiant se tait, le journal la garde.
            Cliquer(DossierGuerre.RETOUR); reponse = RecuIntention.Refusee(400, "cible inconnue : 'plausible-10461-0'");
            UnityEngine.TestTools.LogAssert.Expect(LogType.Log, "GestesDesJauges : raison illisible : cible inconnue : 'plausible-10461-0'");
            Cliquer(DossierGuerre.DECLARER); Cliquer(DossierGuerre.CONFIRMER); Assert.That(dossier.MessageAffiche, Does.EndWith("raison illisible, gardée au journal"));
        }

        // Les textes les plus longs que le monde sert (chaque ordre refusé d'avance, avec sa raison) tiennent au-dessus du
        // curseur ou du bouton qui les suit : aucun ne s'écrit dessous.
        [Test] public void Aucun_texte_des_ordres_ne_passe_sous_la_commande_qui_le_suit()
        {
            Servir(new OrdresDeGuerre(M, 5, new DateDuMonde(1400, 6),
                new LeveeLue(FERMEE, new[] { new LieuDeLevee(10465, 0, 320) }, 500, 17084.9, 2.5), new CibleLue(10461, CIBLE, "vous êtes déjà en guerre avec cette maison"),
                new[] { new OrdresDUneArmee(0, 10465, 0, 1200, 5000, null, null, new MarcheLue("l'armée est déjà à ce lieu", new long[0], 0, 0), "l'armée marche encore : elle assiège une fois arrivée", null, 1200, 5000) }));
            dossier.Afficher(horloge);
            var commandes = dossier.Panneau.GetComponentsInChildren<Selectable>(true).Select(s => s.GetComponent<RectTransform>()).Where(r => r.parent == dossier.Panneau).ToArray();
            Assert.That(commandes.Length, Is.GreaterThanOrEqualTo(10), "curseurs et boutons du panneau");
            foreach (string nom in new[] { DossierGuerre.LEVER, DossierGuerre.DECLARER, "Armée choisie", "Ordres de l'armée", "Message des ordres" })
            {
                var texte = dossier.Panneau.GetComponentsInChildren<Text>(true).Single(t => t.name == nom && t.transform.parent == dossier.Panneau);
                float haut = -texte.rectTransform.anchoredPosition.y, bas = haut + texte.preferredHeight;
                Assert.That(texte.preferredHeight, Is.GreaterThan(0), nom + " : hauteur non mesurée");
                foreach (var commande in commandes.Where(c => -c.anchoredPosition.y > haut))
                    Assert.That(bas, Is.LessThanOrEqualTo(-commande.anchoredPosition.y), "« " + nom + " » passe sous « " + commande.name + " » : " + texte.text);
            }
        }

        [Test] public void Un_ordre_refuse_d_avance_a_sa_commande_inactive_et_dit_pourquoi()
        {
            Servir(Devis(FERMEE, "l'armée marche encore : elle assiège une fois arrivée")); dossier.CurseurHommes.value = 10; dossier.Afficher(horloge);
            Assert.That(dossier.Commande(DossierGuerre.LEVER).interactable || dossier.CurseurHommes.interactable, Is.False);
            Assert.That(dossier.TexteDe(DossierGuerre.LEVER), Does.EndWith("\nRefusé d'avance : " + FERMEE));
            Assert.That(dossier.Commande(DossierGuerre.ASSIEGER).interactable, Is.False); Assert.That(dossier.Commande(DossierGuerre.MARCHER).interactable, Is.True, "contre-épreuve : la marche permise reste active");
            Assert.That(dossier.TexteDe("Ordres de l'armée"), Does.Contain("Assiéger la place où se tient l'armée — refusé d'avance : l'armée marche encore"));
            Cliquer(DossierGuerre.LEVER); Cliquer(DossierGuerre.ASSIEGER); Assert.That(dossier.Ordre.Brouillon, Is.Null, "un ordre refusé d'avance se prépare");
            // Sans terre gardée sur la carte, ni déclaration ni marche : la ligne dit quoi faire.
            gardee = null; Servir(Devis(cible: false)); dossier.Afficher(horloge);
            Assert.That(dossier.Commande(DossierGuerre.DECLARER).interactable || dossier.Commande(DossierGuerre.MARCHER).interactable, Is.False);
            Assert.That(dossier.TexteDe(DossierGuerre.DECLARER), Does.Contain("gardez une terre sur la carte")); Assert.That(dossier.TexteDe("Ordres de l'armée"), Does.StartWith("Marcher : gardez une terre"));
            Assert.That(envoyes, Is.Empty);
        }

        [Test] public void Le_feuillet_dit_mes_guerres_mes_armees_et_mes_prises()
        {
            Servir(Devis()); string recit = dossier.TexteAffiche;
            Assert.That(recit, Does.Contain("VOS GUERRES\nContre Seigneurs du Zab, déclarée par vous, depuis 10 jours")
                .And.Contain("VOS ARMÉES\n1 200 hommes à un lieu sans nom lu · en marche vers un lieu sans nom lu · vivres 5,00 t")
                .And.Contain("TERRES PRISES ET PERDUES\nun lieu sans nom lu prise à Seigneurs du Zab").And.Contain("Relevé au jour 13 de 1400."));
            Assert.That(Illisible(recit), Is.Null, recit);
            Servir(Devis(), new GuerresLues(3, new DateDuMonde(1400, 4), new GuerreLue[0], new ArmeeLue[0], new PriseLue[0], 0));
            Assert.That(dossier.TexteAffiche, Does.Contain("VOS GUERRES\nAucune guerre.").And.Contain("VOS ARMÉES\nAucune armée.").And.Not.Contain("PRISES"));
            Bouton(panneau, DossierGuerre.COMMANDE).onClick.Invoke(); Assert.That(dossier.Feuillet.Ouvert, Is.False, "la commande ne referme pas le feuillet");
        }

        // Dans le cabinet : la commande est dans « Votre maison », chaque commande dit ce qu'elle fait, et le feuillet ne recouvre pas la barre.
        [Test] public void Dans_le_cabinet_le_feuillet_s_ouvre_depuis_votre_maison_sous_la_barre()
        {
            var racine = new GameObject("Carte de contrôle", typeof(CarteDessinee), typeof(HorlogeDeCarte), typeof(FicheDeCellule), typeof(ReperesDeDepart));
            try
            {
                racine.AddComponent<CabinetDeCarte>().Construire(); Transform cabinet = racine.transform.Find("Cabinet");
                var commande = Bouton(cabinet, DossierGuerre.COMMANDE); Assert.That(commande.transform.parent.name, Is.EqualTo("Votre maison"));
                Assert.That(CabinetDeCarte.CommandesSansPhrase(cabinet), Is.Empty);
                commande.onClick.Invoke(); Canvas.ForceUpdateCanvases();
                var feuillet = cabinet.Cast<Transform>().Single(t => t.name == DossierGuerre.TITRE && t.GetComponentInChildren<ScrollRect>(true) != null);
                Assert.That(feuillet.gameObject.activeSelf, Is.True);
                Rect Monde(RectTransform t) { var c = new Vector3[4]; t.GetWorldCorners(c); return Rect.MinMaxRect(c.Min(v => v.x), c.Min(v => v.y), c.Max(v => v.x), c.Max(v => v.y)); }
                Rect barre = Monde((RectTransform)cabinet.Find("FORGE · Le cabinet")); barre = Rect.MinMaxRect(barre.xMin + .5f, barre.yMin + .5f, barre.xMax - .5f, barre.yMax - .5f);
                foreach (var t in new[] { (RectTransform)feuillet, (RectTransform)feuillet.Find(DossierGuerre.ORDRES) }) Assert.That(Monde(t).Overlaps(barre), Is.False, t.name + " recouvre la barre");
                Assert.That(Monde((RectTransform)feuillet.Find(DossierGuerre.ORDRES)).Overlaps(Monde((RectTransform)cabinet.Find("Votre maison"))), Is.False, "les ordres recouvrent « Votre maison »");
            }
            finally { Object.DestroyImmediate(racine); }
        }
    }
}
