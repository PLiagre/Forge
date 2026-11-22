using System;
using System.Collections.Generic;
using System.Linq;

namespace Forge.Pont
{
    // L'outil en main dans la ville. Bâtiment (1, 2, 3) et Enceinte (E) restent des raccourcis du clavier, sans bouton.
    public enum OutilDeLaVille { Aucun, Rue, Parcelle, Caserne, Batiment, Enceinte }
    // Les gestes qui ont un bouton.
    public enum GesteDeLaVille { Rue, Parcelle, Caserne, Valider, Annuler, Retour }
    // La caserne de la capitale : aucune, déposée au monde en attente du tick, au plan en chantier, ou bâtie.
    public enum CaserneDeLaVille { Aucune, Deposee, EnChantier, Batie }
    // Ce que le dernier geste a rendu : rien, un refus (de l'outil, du relief ou du monde), un avis de l'outil, un dépôt accepté.
    public enum IssueDuGeste { Aucune, Refus, Avis, Depot }

    // Ce que l'outil de la ville sait à l'instant : l'outil en main et ses points, l'issue du dernier geste,
    // le devis de la caserne servi par le monde (ou la cause de son absence) et l'état de la caserne au plan.
    public sealed class EtatDesOutils
    {
        public OutilDeLaVille Outil; public int Points; public string Nature; // Nature : le bâtiment en main, hors du mode bâtiment null
        public IssueDuGeste Issue; public string Texte; // Texte : le refus ou l'avis, tel que l'outil l'écrit
        public BatimentDeLevee Devis; public string AbsenceDuDevis; public CaserneDeLaVille Caserne;
        public bool RetourDemande;
    }

    // Un bouton tel qu'il doit se montrer : visible, enfoncé (l'outil en main), actif, son libellé et la raison de son état.
    public readonly struct BoutonCompose
    {
        public GesteDeLaVille Geste { get; } public bool Visible { get; } public bool Enfonce { get; } public bool Actif { get; }
        public string Libelle { get; } public string Raison { get; }
        public BoutonCompose(GesteDeLaVille geste, bool visible, bool enfonce, bool actif, string libelle, string raison)
        { Geste = geste; Visible = visible; Enfonce = enfonce; Actif = actif; Libelle = libelle; Raison = raison; }
    }

    public sealed class CompositionDesOutils
    {
        public IReadOnlyList<BoutonCompose> Boutons { get; } public string Ligne { get; }
        public CompositionDesOutils(IReadOnlyList<BoutonCompose> boutons, string ligne) { Boutons = boutons; Ligne = ligne; }
        public BoutonCompose this[GesteDeLaVille geste] => Boutons.First(b => b.Geste == geste);
    }

    // Les outils de la ville en boutons, sans clavier ni scène : ce que montre chaque bouton et la seule ligne d'aide, d'après
    // l'état de l'outil. Rien n'est calculé ici : le prix et le grain qui manque sont ceux du devis servi par le monde.
    // Chaque ligne passe le juge du clerc (`TexteDuMonde.Refus`) : ni identifiant, ni nombre sans unité.
    public static class OutilsDeLaVille
    {
        // Les six gestes à bouton, leur nom et la touche qui les raccourcit, écrite sur le bouton.
        public static readonly IReadOnlyList<(GesteDeLaVille geste, string nom, string raccourci)> Gestes = new[]
        {
            (GesteDeLaVille.Rue, "Rue", "R"), (GesteDeLaVille.Parcelle, "Parcelle", "P"), (GesteDeLaVille.Caserne, "Caserne", "4"),
            (GesteDeLaVille.Valider, "Valider", "Entrée"), (GesteDeLaVille.Annuler, "Annuler", "Échap"), (GesteDeLaVille.Retour, "Retour à la carte", "C"),
        };
        public const string SANS_OUTIL = "Choisissez un outil : Rue, Parcelle ou Caserne.";
        public const string GESTE_REFUSE = "Ce geste est refusé."; // un refus dont même le début montre un identifiant ou un nombre nu

        public static string Libelle(GesteDeLaVille geste)
        {
            var (_, nom, raccourci) = Gestes.First(g => g.geste == geste);
            return nom + " (" + raccourci + ")";
        }

        public static CompositionDesOutils Composer(EtatDesOutils e)
        {
            if (e == null) throw new ArgumentNullException(nameof(e));
            var caserne = Caserne(e);
            bool trace = e.Outil == OutilDeLaVille.Rue || e.Outil == OutilDeLaVille.Parcelle || e.Outil == OutilDeLaVille.Enceinte;
            string manquent = Manquent(e);
            var boutons = new List<BoutonCompose>();
            foreach (var (geste, _, _) in Gestes)
            {
                string libelle = Libelle(geste);
                switch (geste)
                {
                    case GesteDeLaVille.Rue: boutons.Add(new BoutonCompose(geste, true, e.Outil == OutilDeLaVille.Rue, true, libelle, null)); break;
                    case GesteDeLaVille.Parcelle: boutons.Add(new BoutonCompose(geste, true, e.Outil == OutilDeLaVille.Parcelle, true, libelle, null)); break;
                    case GesteDeLaVille.Caserne: boutons.Add(new BoutonCompose(geste, true, e.Outil == OutilDeLaVille.Caserne, caserne.actif, libelle + "\n" + caserne.detail, caserne.raison)); break;
                    // Valider ne sert qu'aux outils qui tracent ; la caserne et le bâtiment se posent d'un clic sur leur parcelle.
                    case GesteDeLaVille.Valider: boutons.Add(new BoutonCompose(geste, trace, false, trace && manquent == null, libelle, manquent)); break;
                    case GesteDeLaVille.Annuler: boutons.Add(new BoutonCompose(geste, e.Outil != OutilDeLaVille.Aucun, false, true, libelle, null)); break;
                    case GesteDeLaVille.Retour: boutons.Add(new BoutonCompose(geste, true, false, !e.RetourDemande, libelle, e.RetourDemande ? "La carte s'ouvre." : null)); break;
                }
            }
            return new CompositionDesOutils(boutons, Ligne(e, caserne));
        }

        // Ce qui manque pour valider le tracé en cours ; null s'il est complet.
        static string Manquent(EtatDesOutils e)
        {
            int n = Math.Max(0, e.Points);
            switch (e.Outil)
            {
                case OutilDeLaVille.Rue: return n >= 2 ? null : "Il faut au moins deux points.";
                case OutilDeLaVille.Parcelle: return n >= 2 ? null : "Il faut deux coins.";
                case OutilDeLaVille.Enceinte: return n >= 3 ? null : "Il faut au moins trois coins.";
                default: return null;
            }
        }

        // Le bouton de la caserne : sa caserne déjà au plan ou déposée, sinon son devis. Grisée, elle dit pourquoi en peu de mots
        // (le grain qui manque, ou le début du refus du monde) ; la raison entière sert la ligne d'aide quand l'outil est en main.
        static (bool actif, string detail, string raison) Caserne(EtatDesOutils e)
        {
            switch (e.Caserne)
            {
                case CaserneDeLaVille.Deposee: return (false, "déposée", "Caserne déposée : son chantier s'ouvre demain.");
                case CaserneDeLaVille.EnChantier: return (false, "en chantier", "La caserne est en chantier.");
                case CaserneDeLaVille.Batie: return (false, "bâtie", "La caserne est bâtie.");
            }
            var d = e.Devis;
            if (d == null) return (false, "prix non lu", "Prix de la caserne non lu : " + TexteDuMonde.Absence(e.AbsenceDuDevis ?? "le monde n'a pas encore répondu"));
            if (d.ManqueKg > 0)
            {
                string manque = TexteDuMonde.Masse(d.ManqueKg);
                return (false, "il manque " + manque + " de grain", "Le grenier ne paie pas la caserne : il manque " + manque + " de grain.");
            }
            string prix = TexteDuMonde.Masse(d.CoutKg) + " de grain";
            if (d.Refus == null) return (true, prix, null);
            return (false, Tete(d.Refus), TexteDuMonde.Refus("Caserne refusée : " + d.Refus) ?? "Caserne refusée.");
        }

        // Le début d'un refus du monde (« pas assez de bras »), assez court pour un bouton ; s'il montre un identifiant ou un
        // nombre sans unité, le bouton dit seulement que le monde la refuse.
        static string Tete(string refus)
        {
            int fin = refus.IndexOf(" : ", StringComparison.Ordinal);
            string tete = fin > 0 ? refus.Substring(0, fin) : refus;
            return TexteDuMonde.Interdit(tete) == null && TexteDuMonde.SansUnite(tete) == null ? tete : "refusée aujourd'hui";
        }

        // La seule ligne d'aide : le refus du dernier geste, son dépôt, l'avis de l'outil, la raison d'une caserne grisée en main,
        // sinon le geste suivant de l'outil.
        static string Ligne(EtatDesOutils e, (bool actif, string detail, string raison) caserne)
        {
            switch (e.Issue)
            {
                case IssueDuGeste.Refus: return string.IsNullOrWhiteSpace(e.Texte) ? GESTE_REFUSE : TexteDuMonde.Refus(e.Texte) ?? GESTE_REFUSE;
                case IssueDuGeste.Depot: return Depot(e.Outil) ?? Suivant(e);
                case IssueDuGeste.Avis:
                    if (!string.IsNullOrWhiteSpace(e.Texte) && TexteDuMonde.Refus(e.Texte) is string avis) return avis;
                    break;
            }
            if (e.Outil == OutilDeLaVille.Caserne && !caserne.actif) return caserne.raison;
            return Suivant(e);
        }

        static string Depot(OutilDeLaVille outil)
        {
            switch (outil)
            {
                case OutilDeLaVille.Rue: return "Rue déposée : elle se trace demain.";
                case OutilDeLaVille.Parcelle: return "Parcelle déposée : elle se dessine demain.";
                case OutilDeLaVille.Caserne: return "Caserne déposée : son chantier s'ouvre demain.";
                case OutilDeLaVille.Batiment: return "Bâtiment déposé : son chantier s'ouvre demain.";
                case OutilDeLaVille.Enceinte: return "Enceinte déposée : elle se dessine demain.";
                default: return null;
            }
        }

        static string Suivant(EtatDesOutils e)
        {
            int n = Math.Max(0, e.Points);
            switch (e.Outil)
            {
                case OutilDeLaVille.Rue:
                    return n == 0 ? "Cliquez le départ de la rue." : n == 1 ? "Cliquez le point suivant de la rue." : "Cliquez un autre point, ou Valider pour tracer la rue.";
                case OutilDeLaVille.Parcelle:
                    return n == 0 ? "Cliquez un coin de la parcelle, au bord d'une rue." : n == 1 ? "Cliquez le coin opposé, au fond de la parcelle."
                        : "Valider pour déposer la parcelle, ou cliquez un autre coin du fond.";
                case OutilDeLaVille.Caserne: return "Cliquez une parcelle achevée pour y poser la caserne.";
                case OutilDeLaVille.Batiment: return "Cliquez une parcelle achevée pour y poser un bâtiment : " + (string.IsNullOrWhiteSpace(e.Nature) ? "à choisir" : e.Nature) + ".";
                case OutilDeLaVille.Enceinte:
                    return n < 3 ? "Cliquez les coins du mur : " + n + (n > 1 ? " coins posés" : " coin posé") + ", trois au moins." : "Cliquez un autre coin, ou Valider pour déposer l'enceinte.";
                default: return SANS_OUTIL;
            }
        }
    }
}
