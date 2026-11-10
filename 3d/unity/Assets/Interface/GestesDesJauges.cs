using System;
using System.Globalization;
using System.Linq;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    // Lot #1046 : à droite du feuillet « Le pays », le panneau « Gestes des jauges ». Chaque geste du pays dit son prix en points, son effet et la raison de son
    // refus, servie par `/pays` au tick du monde lu. Le geste confirmé dépose `depenser_jauge` par `POST /intention`, le chemin de l'IA et de la main ;
    // un refus du service s'affiche, avec sa raison, dans l'état « × Demande refusée » du socle. Le panneau est un enfant du feuillet : il s'ouvre et se ferme avec lui.
    public sealed class GestesDesJauges : MonoBehaviour
    {
        public const string TITRE = "Gestes des jauges", CONFIRMER = "Confirmer le geste", RETOUR = "Retour aux gestes";
        const string ILLISIBLE = "raison illisible, gardée au journal";
        const int LIGNES = 2;
        const float LARGEUR = 452, HAUTEUR_COMMANDE = 44;

        [Serializable] sealed class DepenserJauge { public string type = "depenser_jauge", maison, geste; }

        Func<Lecture<MondeAvecMaisonLu>> monde;
        Func<Lecture<GestesDuPays>> gestes;
        Text etat, message;
        readonly Text[] textes = new Text[LIGNES];
        readonly Button[] boutons = new Button[LIGNES];
        Button confirmer, retour;
        // Les deux premiers gestes de la dernière lecture présente : ils nomment les lignes, même quand leur tick n'est plus celui du monde.
        readonly GesteLu[] connus = new GesteLu[LIGNES];
        // Le geste préparé, et la maison pour laquelle il l'a été.
        GesteLu choisi; string maisonChoisie;
        RecuIntention recuVu; EtatLecture? etatDuRecu; string texteDuRecu;
        bool excedentJournalise;

        public RectTransform Panneau { get; private set; }
        public OrdreConfirme Ordre { get; private set; }
        public string EtatAffiche => etat == null ? "" : etat.text;
        public string MessageAffiche => message == null ? "" : message.text;
        public Button BoutonConfirmer => confirmer;
        public Button BoutonRetour => retour;
        public string TexteDuGeste(string id) { int i = Ligne(id); return i < 0 ? "" : textes[i].text; }
        public Button BoutonDuGeste(string id) { int i = Ligne(id); return i < 0 ? null : boutons[i]; }
        int Ligne(string id) { for (int i = 0; i < LIGNES; i++) if (connus[i] != null && connus[i].Id == id) return i; return -1; }

        public void Initialiser(RectTransform cadre, Func<Lecture<MondeAvecMaisonLu>> monde, Func<Lecture<GestesDuPays>> gestes, OrdreConfirme ordre)
        {
            this.monde = monde ?? throw new ArgumentNullException(nameof(monde)); this.gestes = gestes ?? throw new ArgumentNullException(nameof(gestes));
            Ordre = ordre ?? throw new ArgumentNullException(nameof(ordre));
            Panneau = SocleInterface.Panneau(cadre, TITRE, 764, 0, 500, 640);
            etat = SocleInterface.Texte(Panneau, "Lecture des gestes…", 24, 88, LARGEUR); etat.name = "État des gestes";
            etat.rectTransform.sizeDelta = new Vector2(LARGEUR, 32); etat.verticalOverflow = VerticalWrapMode.Overflow;
            for (int i = 0; i < LIGNES; i++)
            {
                int ligne = i;
                textes[i] = SocleInterface.Texte(Panneau, "", 24, 124 + 172 * i, LARGEUR, 16); textes[i].name = "Texte du geste " + (i + 1);
                textes[i].rectTransform.sizeDelta = new Vector2(LARGEUR, 116);
                boutons[i] = Bouton("Geste " + (i + 1), 24, 240 + 172 * i, LARGEUR, () => Choisir(ligne), "Prépare ce geste sans le payer ; « " + CONFIRMER + " » le paie.");
            }
            message = SocleInterface.Texte(Panneau, "", 24, 468, LARGEUR); message.name = "Message des gestes";
            message.rectTransform.sizeDelta = new Vector2(LARGEUR, 96);
            retour = Bouton(RETOUR, 24, 572, 220, () => { Ordre.Recommencer(); choisi = null; maisonChoisie = null; },
                "Abandonne le geste préparé, ou referme son reçu ; rien n'est payé.");
            confirmer = Bouton(CONFIRMER, 256, 572, 220, Confirmer, "Paie le geste préparé : le monde le règle au jour suivant.");
            MatieresCabinet.Engagement(confirmer);
            foreach (var texte in Panneau.GetComponentsInChildren<Text>(true)) texte.supportRichText = false;
            Pas();
        }

        Button Bouton(string nom, float x, float y, float largeur, Action action, string phrase)
        {
            var b = SocleInterface.Commande(Panneau, nom, x, y, action, phrase: phrase);
            b.GetComponent<RectTransform>().sizeDelta = new Vector2(largeur, HAUTEUR_COMMANDE);
            b.GetComponentInChildren<Text>().rectTransform.sizeDelta = new Vector2(largeur, HAUTEUR_COMMANDE);
            return b;
        }

        void LateUpdate() { if (Panneau != null) Pas(); }

        // Les états, dans l'ordre de `DossierPays.Decrire` : 1 à 5 attendent ou se taisent, 6 écrit les gestes.
        int Etat(out string texte)
        {
            var m = monde(); var g = gestes();
            if (m == null) { texte = "Lecture des gestes…"; return 1; }
            if (!m.Presente) { texte = "Gestes indisponibles : " + TexteDuMonde.Absence(m.Absence); return 2; }
            string id = m.Donnees.MaisonDuJoueur;
            if (id == null) { texte = "Choisissez une maison pour dépenser ses points."; return 3; }
            if (g == null || g.Presente && (g.Donnees.MaisonId != id || g.Donnees.Tick != m.Donnees.Monde.Tick)) { texte = "Gestes en attente du monde"; return 4; }
            if (!g.Presente) { texte = "Gestes indisponibles : " + TexteDuMonde.Absence(g.Absence, id); return 5; }
            texte = g.Donnees.Pays.Nom + " · relevé au " + TexteDuMonde.Date(g.Donnees.Pays.Date);
            return 6;
        }

        // Récrit tout, à chaque image.
        public void Pas()
        {
            int code = Etat(out string texte);
            etat.text = texte;
            var lus = gestes();
            if (lus != null && lus.Presente)
            {
                for (int i = 0; i < LIGNES; i++) connus[i] = i < lus.Donnees.Gestes.Count ? lus.Donnees.Gestes[i] : null;
                if (lus.Donnees.Gestes.Count > LIGNES && !excedentJournalise)
                {
                    excedentJournalise = true;
                    Debug.Log("GestesDesJauges : " + lus.Donnees.Gestes.Count.ToString(CultureInfo.InvariantCulture) + " gestes servis, " + LIGNES + " montrés");
                }
            }
            bool libre = Ordre.Brouillon == null && Ordre.Recu == null && !Ordre.EnCours;
            for (int i = 0; i < LIGNES; i++)
            {
                var g = connus[i];
                boutons[i].gameObject.SetActive(g != null);
                textes[i].gameObject.SetActive(g != null);
                textes[i].text = g != null && code == 6 ? Geste(g, lus.Donnees.Pays) : "";
                boutons[i].interactable = g != null && code == 6 && g.Refus == null && libre;
                if (g == null) continue;
                boutons[i].name = g.Nom; boutons[i].GetComponentInChildren<Text>().text = g.Nom;
                boutons[i].GetComponent<Infobulle>().phrase = g.Nom + " : prépare ce geste sans le payer ; « " + CONFIRMER + " » le paie.";
            }
            string id = monde()?.Presente == true ? monde().Donnees.MaisonDuJoueur : null;
            bool brouillon = Ordre.Brouillon != null, recu = Ordre.Recu != null;
            confirmer.gameObject.SetActive(brouillon && !recu);
            confirmer.interactable = !Ordre.EnCours && code == 6 && maisonChoisie != null && maisonChoisie == id;
            retour.gameObject.SetActive(brouillon || recu);
            retour.interactable = (brouillon || recu) && !Ordre.EnCours;
            Message();
            message.rectTransform.sizeDelta = new Vector2(LARGEUR, 96); // `EtatsLecture` le règle sur le texte : la boîte reste celle du brief
        }

        void Message()
        {
            if (Ordre.EnCours) { Normal("Envoi en cours. Attendez le reçu."); return; }
            if (!ReferenceEquals(Ordre.Recu, recuVu)) { recuVu = Ordre.Recu; Noter(recuVu); } // écrit une fois : le tick qui avance ne le redate pas
            if (Ordre.Recu != null)
            {
                if (etatDuRecu == null) Normal(texteDuRecu); else EtatsLecture.Afficher(message, etatDuRecu.Value, texteDuRecu);
            }
            else if (Ordre.Brouillon != null) Normal(Ordre.Resume);
            else Normal("Choisissez un geste : son prix se paie à la confirmation.");
        }

        void Normal(string texte) { message.text = texte; message.color = SocleInterface.Couleur("encre"); }

        // La phrase du reçu, tirée à son arrivée : acceptée, refusée avec sa raison en points, ou absente avec sa cause.
        void Noter(RecuIntention recu)
        {
            etatDuRecu = null; texteDuRecu = null;
            if (recu == null) return;
            string nom = choisi?.Nom ?? "Geste";
            if (recu.Acceptee)
            {
                var lus = gestes();
                bool date = lus != null && lus.Presente && lus.Donnees.Tick == recu.AppliqueeAuTick;
                if (!date) Debug.Log("GestesDesJauges : geste reçu après le tick " + recu.AppliqueeAuTick.Value.ToString(CultureInfo.InvariantCulture) + ", gestes " + (lus != null && lus.Presente ? "lus au tick " + lus.Donnees.Tick.ToString(CultureInfo.InvariantCulture) : "non lus"));
                texteDuRecu = nom + " : geste reçu" + (date ? " au " + TexteDuMonde.Date(lus.Donnees.Pays.Date) : "") + ". Le monde le paie au jour suivant.";
            }
            else if (recu.Presente) { etatDuRecu = EtatLecture.Refus; texteDuRecu = nom + " : " + Raison(recu.Erreur, maisonChoisie); }
            else { etatDuRecu = EtatLecture.Panne; texteDuRecu = "Envoi non confirmé : " + TexteDuMonde.Absence(recu.Absence) + ". Vérifiez le monde avant tout nouveau geste."; }
        }

        void Choisir(int ligne)
        {
            if (Etat(out _) != 6) return;
            var lus = gestes().Donnees;
            if (ligne >= lus.Gestes.Count || Ordre.Brouillon != null || Ordre.Recu != null || Ordre.EnCours) return;
            var g = lus.Gestes[ligne];
            if (g.Refus != null) return;
            string id = monde().Donnees.MaisonDuJoueur;
            if (Ordre.Preparer(Intention(id, g.Id), Resume(g, lus.Pays))) { choisi = g; maisonChoisie = id; }
        }

        void Confirmer()
        {
            if (Ordre.EnCours || Ordre.Brouillon == null || Ordre.Recu != null || Etat(out _) != 6) return;
            if (maisonChoisie == null || maisonChoisie != monde().Donnees.MaisonDuJoueur) return;
            _ = Ordre.Confirmer();
        }

        // Le dépôt du geste : `{"type":"depenser_jauge","maison":…,"geste":…}`, les octets que le service lit de la main de l'IA comme de la nôtre.
        public static string Intention(string maison, string geste)
        {
            if (string.IsNullOrWhiteSpace(maison)) throw new ArgumentException("Maison non confirmée par le monde", nameof(maison));
            if (string.IsNullOrWhiteSpace(geste)) throw new ArgumentException("Geste absent", nameof(geste));
            return JsonUtility.ToJson(new DepenserJauge { maison = maison, geste = geste });
        }

        // Quatre lignes : le nom, le prix, l'effet, puis « Payable aujourd'hui » ou la raison du refus d'avance.
        public static string Geste(GesteLu g, PaysLu p)
        {
            string prix = string.Join(" et ", g.Cout.Select(c => TexteDuMonde.Points(c.Value) + " de " + p.Points[c.Key].Nom + " (en réserve : " + TexteDuMonde.Points(p.Points[c.Key].Valeur) + ")"));
            string effet = string.Join(" et ", g.Effet.Select(e => Ecart(e.Value) + " de " + p.Jauges[e.Key].Nom + " (aujourd'hui : " + TexteDuMonde.Points(p.Jauges[e.Key].Valeur) + ")"));
            return g.Nom + "\nPrix : " + prix + "\nEffet : " + effet + "\n" + (g.Refus == null ? "Payable aujourd'hui" : "Refusé d'avance : " + Raison(g.Refus, p.MaisonId));
        }

        // La phrase que le joueur relit avant de confirmer.
        static string Resume(GesteLu g, PaysLu p) =>
            g.Nom + " : " + string.Join(" et ", g.Cout.Select(c => TexteDuMonde.Points(c.Value) + " de " + p.Points[c.Key].Nom))
            + " pour " + string.Join(" et ", g.Effet.Select(e => Ecart(e.Value) + " de " + p.Jauges[e.Key].Nom)) + ". Confirmez pour payer.";

        static string Ecart(double v) => (v > 0 ? "+" : "") + TexteDuMonde.Points(v);

        // La raison du monde telle quelle, si elle ne montre ni identifiant ni nombre nu ; sinon le joueur ne la lit pas, et le journal la garde.
        public static string Raison(string raison, string maison)
        {
            if (raison != null && !string.IsNullOrWhiteSpace(raison)
                && (maison == null ? TexteDuMonde.Interdit(raison) : TexteDuMonde.Interdit(raison, maison)) == null && TexteDuMonde.SansUnite(raison) == null) return raison;
            Debug.Log("GestesDesJauges : raison illisible : " + raison);
            return ILLISIBLE;
        }
    }
}
