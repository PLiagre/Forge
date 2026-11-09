using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Forge.Pont;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using UnityEngine.UI;

namespace Forge.Interface.Tests
{
    // Lot #1046 : le panneau « Gestes des jauges » dit prix, effet et refus de chaque geste du pays, puis dépose `depenser_jauge` ou montre le refus du service.
    public sealed class GestesDesJaugesTests
    {
        const string Bar = "seigneurie-1", ASSEOIR = "asseoir_le_droit", AFFERMIR = "affermir_la_concorde";
        const string LITTERAL = "{\"type\":\"depenser_jauge\",\"maison\":\"seigneurie-1\",\"geste\":\"asseoir_le_droit\"}";
        const string REFUS_SCEAU = "pas assez de points de Sceau : 30 points demandés, 1,5 point disponible";
        const string REFUS_PLUME = "pas assez de points de Plume : 50 points demandés, 35 points disponibles";
        static readonly DateDuMonde Date = new DateDuMonde(1400, 212);

        GameObject racine; GestesDesJauges panneau;
        Lecture<MondeAvecMaisonLu> monde; Lecture<GestesDuPays> gestes;
        readonly List<string> envoyes = new List<string>(); Func<string, Task<RecuIntention>> envoi;

        static Lecture<MondeAvecMaisonLu> Monde(long tick, string maison = Bar) => Lecture<MondeAvecMaisonLu>.De(
            new MondeAvecMaisonLu(new MondeLu(tick, Date, 1, new[] { new CelluleDuMonde(7, 12, -1, -1) }), maison));
        static JaugeLue Jauge(string nom, double v, double min, double max, double neutre) => new JaugeLue(nom, "ce que dit " + nom, v, min, max, neutre);
        static PointsLus Reserve(string nom, double v, string domaine) => new PointsLus(nom, "ce que dit " + nom, v, 999, domaine, null);
        // Bar au tick 211 : Plume 35, Sceau 31,5, Concorde 0, Droit 50 ; la Concorde est refusée d'avance, le Droit se paie.
        static GestesDuPays Gestes(string maison = Bar, long tick = 211)
        {
            var pays = new PaysLu(maison, "Bar", tick, Date,
                new Dictionary<string, JaugeLue> { { "concorde", Jauge("Concorde", 0, -3, 3, 0) }, { "renom", Jauge("Renom", 0, 0, 100, 0) }, { "droit", Jauge("Droit", 50, 0, 100, 50) } },
                new Dictionary<string, PointsLus> { { "plume", Reserve("Plume", 35, "gestion") }, { "sceau", Reserve("Sceau", 31.5, "diplomatie") }, { "epee", Reserve("Épée", 7, "guerre") } },
                null, "chef de la maison non connu : aucun point", new PoseLue[0]);
            return new GestesDuPays(pays, new[]
            {
                new GesteLu(AFFERMIR, "Affermir la concorde", new Dictionary<string, double> { { "plume", 50 } }, new Dictionary<string, double> { { "concorde", 1 } }, REFUS_PLUME),
                new GesteLu(ASSEOIR, "Asseoir le droit", new Dictionary<string, double> { { "sceau", 30 } }, new Dictionary<string, double> { { "droit", 10 } }, null),
            });
        }

        [SetUp] public void Monter()
        {
            monde = Monde(211); gestes = Lecture<GestesDuPays>.De(Gestes()); envoyes.Clear();
            envoi = json => { envoyes.Add(json); return Task.FromResult(RecuIntention.AccepteeAu(211)); };
            racine = new GameObject("Preuve 1046", typeof(RectTransform)); panneau = racine.AddComponent<GestesDesJauges>();
            panneau.Initialiser((RectTransform)racine.transform, () => monde, () => gestes, new OrdreConfirme(json => envoi(json)));
            panneau.Pas();
        }
        [TearDown] public void Fermer() => UnityEngine.Object.DestroyImmediate(racine);

        static void Propre(string texte) => Assert.That(TexteDuMonde.Interdit(texte, Bar) ?? TexteDuMonde.SansUnite(texte), Is.Null, texte);

        [Test] public void Chaque_geste_dit_son_prix_son_effet_et_son_refus()
        {
            var lus = Gestes(); var pays = lus.Pays;
            string droit = GestesDesJauges.Geste(lus.Gestes[1], pays), concorde = GestesDesJauges.Geste(lus.Gestes[0], pays);
            Assert.That(droit, Is.EqualTo("Asseoir le droit\nPrix : 30 points de Sceau (en réserve : 31,5 points)\nEffet : +10 points de Droit (aujourd'hui : 50 points)\nPayable aujourd'hui"));
            Assert.That(concorde, Is.EqualTo("Affermir la concorde\nPrix : 50 points de Plume (en réserve : 35 points)\nEffet : +1 point de Concorde (aujourd'hui : 0 point)\nRefusé d'avance : " + REFUS_PLUME));
            Propre(droit); Propre(concorde);
            LogAssert.Expect(LogType.Log, "GestesDesJauges : raison illisible : maison inconnue ou mal formée : 'seigneurie-1'");
            Assert.That(GestesDesJauges.Raison("maison inconnue ou mal formée : 'seigneurie-1'", Bar), Is.EqualTo("raison illisible, gardée au journal"));
            Assert.That(GestesDesJauges.Raison(REFUS_SCEAU, Bar), Is.EqualTo(REFUS_SCEAU));
            Assert.That(GestesDesJauges.Intention(Bar, ASSEOIR), Is.EqualTo(LITTERAL));
            Assert.That(panneau.TexteDuGeste(ASSEOIR), Is.EqualTo(droit)); Assert.That(panneau.TexteDuGeste(AFFERMIR), Is.EqualTo(concorde));
            Assert.That(panneau.EtatAffiche, Is.EqualTo("Bar · relevé au jour 212 de 1400"));
            foreach (var t in racine.GetComponentsInChildren<Text>(true)) Assert.That(t.supportRichText, Is.False, t.name);
        }

        [Test] public void Le_geste_confirme_depose_depenser_jauge()
        {
            Assert.That(panneau.BoutonDuGeste(ASSEOIR).interactable, Is.True); Assert.That(panneau.BoutonDuGeste(AFFERMIR).interactable, Is.False, "un refus servi éteint le bouton");
            panneau.BoutonDuGeste(AFFERMIR).onClick.Invoke(); Assert.That(panneau.Ordre.Brouillon, Is.Null, "le clic d'un geste refusé ne prépare rien");
            Assert.That(panneau.BoutonConfirmer.gameObject.activeSelf, Is.False); Assert.That(panneau.BoutonRetour.gameObject.activeSelf, Is.False);
            Assert.That(panneau.MessageAffiche, Is.EqualTo("Choisissez un geste : son prix se paie à la confirmation."));
            panneau.BoutonDuGeste(ASSEOIR).onClick.Invoke(); panneau.Pas();
            Assert.That(panneau.MessageAffiche, Is.EqualTo("Asseoir le droit : 30 points de Sceau pour +10 points de Droit. Confirmez pour payer."));
            Assert.That(envoyes, Is.Empty, "rien ne part avant la confirmation");
            Assert.That(panneau.BoutonDuGeste(ASSEOIR).interactable, Is.False, "un brouillon éteint les gestes"); Assert.That(panneau.BoutonConfirmer.interactable, Is.True);
            panneau.BoutonConfirmer.onClick.Invoke(); panneau.Pas();
            Assert.That(envoyes, Is.EqualTo(new[] { LITTERAL })); Assert.That(GestesDesJauges.Intention(Bar, ASSEOIR), Is.EqualTo(LITTERAL));
            Assert.That(panneau.MessageAffiche, Is.EqualTo("Asseoir le droit : geste reçu au jour 212 de 1400. Le monde le paie au jour suivant."));
            Assert.That(panneau.BoutonDuGeste(ASSEOIR).interactable || panneau.BoutonDuGeste(AFFERMIR).interactable, Is.False, "les gestes attendent « Retour aux gestes »");
            Assert.That(panneau.BoutonConfirmer.gameObject.activeSelf, Is.False); Assert.That(panneau.BoutonRetour.interactable, Is.True);
            monde = Monde(212); panneau.Pas(); // l'horloge qui avance ne redate pas le reçu
            Assert.That(panneau.MessageAffiche, Is.EqualTo("Asseoir le droit : geste reçu au jour 212 de 1400. Le monde le paie au jour suivant."));
            panneau.BoutonRetour.onClick.Invoke(); monde = Monde(211); panneau.Pas();
            Assert.That(panneau.BoutonDuGeste(ASSEOIR).interactable, Is.True);
        }

        [Test] public void Un_refus_du_service_s_affiche_dans_l_etat_du_socle()
        {
            void Deposer(RecuIntention recu)
            {
                envoi = _ => Task.FromResult(recu);
                panneau.BoutonDuGeste(ASSEOIR).onClick.Invoke(); panneau.Pas(); panneau.BoutonConfirmer.onClick.Invoke(); panneau.Pas();
            }
            Deposer(RecuIntention.Refusee(400, REFUS_SCEAU));
            Assert.That(panneau.MessageAffiche, Is.EqualTo("× Demande refusée\nAsseoir le droit : " + REFUS_SCEAU));
            Assert.That(racine.GetComponentsInChildren<Text>(true).Single(t => t.name == "Message des gestes").color, Is.EqualTo(SocleInterface.Couleur("alerte")));
            panneau.BoutonRetour.onClick.Invoke(); panneau.Pas();
            Assert.That(racine.GetComponentsInChildren<Text>(true).Single(t => t.name == "Message des gestes").color, Is.EqualTo(SocleInterface.Couleur("encre")), "le message revient en encre");
            LogAssert.Expect(LogType.Log, "GestesDesJauges : raison illisible : maison inconnue ou mal formée : 'seigneurie-1'");
            Deposer(RecuIntention.Refusee(400, "maison inconnue ou mal formée : 'seigneurie-1'"));
            Assert.That(panneau.MessageAffiche, Is.EqualTo("× Demande refusée\nAsseoir le droit : raison illisible, gardée au journal"));
            panneau.BoutonRetour.onClick.Invoke(); panneau.Pas();
            Deposer(RecuIntention.Absente("service coupé"));
            StringAssert.StartsWith("! Le monde ne répond pas\nEnvoi non confirmé : ", panneau.MessageAffiche);
            StringAssert.EndsWith(". Vérifiez le monde avant tout nouveau geste.", panneau.MessageAffiche);
            panneau.BoutonRetour.onClick.Invoke(); panneau.Pas();
            Assert.That(panneau.MessageAffiche, Is.EqualTo("Choisissez un geste : son prix se paie à la confirmation."));
        }

        [Test] public void Le_panneau_attend_le_meme_tick()
        {
            void Muet(string etat)
            {
                panneau.Pas(); Assert.That(panneau.EtatAffiche, Is.EqualTo(etat));
                foreach (string id in new[] { ASSEOIR, AFFERMIR })
                {
                    Assert.That(panneau.TexteDuGeste(id), Is.Empty, etat); Assert.That(panneau.BoutonDuGeste(id)?.interactable ?? false, Is.False, etat);
                }
                panneau.BoutonDuGeste(ASSEOIR)?.onClick.Invoke(); Assert.That(panneau.Ordre.Brouillon, Is.Null, "aucun clic ne prépare rien : " + etat);
            }
            monde = null; Muet("Lecture des gestes…");
            monde = Lecture<MondeAvecMaisonLu>.Absent("service coupé"); Muet("Gestes indisponibles : service coupé");
            monde = Monde(211, null); Muet("Choisissez une maison pour dépenser ses points.");
            monde = Monde(211); gestes = null; Muet("Gestes en attente du monde");
            gestes = Lecture<GestesDuPays>.De(Gestes(tick: 210)); Muet("Gestes en attente du monde");
            gestes = Lecture<GestesDuPays>.De(Gestes(tick: 212)); Muet("Gestes en attente du monde");
            gestes = Lecture<GestesDuPays>.De(Gestes("grande-3")); Muet("Gestes en attente du monde");
            gestes = Lecture<GestesDuPays>.Absent("service coupé"); Muet("Gestes indisponibles : service coupé");
            gestes = Lecture<GestesDuPays>.De(Gestes()); panneau.Pas();
            Assert.That(panneau.EtatAffiche, Is.EqualTo("Bar · relevé au jour 212 de 1400")); Assert.That(panneau.BoutonDuGeste(ASSEOIR).interactable, Is.True);
        }
    }
}
