using System;
using System.Threading.Tasks;

namespace Forge.Pont
{
    // Le devis de la caserne que la ville affiche sur son bouton : la maison du joueur (`/monde`), puis le bâtiment de levée
    // de ses ordres (`/guerres/ordres`), tels que le monde les sert. Une lecture à la fois, hors du fil principal, au plus une
    // par `PERIODE_S` ; `Pas` recueille la lecture finie sur le fil de l'appelant. Sans devis, `Absence` en nomme la cause.
    public sealed class DevisDeLaCaserne
    {
        public const double PERIODE_S = 1;
        static readonly TimeSpan Delai = TimeSpan.FromSeconds(2);
        sealed class Lu { public BatimentDeLevee Devis; public string Absence; }

        readonly int port; Task<Lu> tache; double prochaine = double.NegativeInfinity;
        public BatimentDeLevee Devis { get; private set; }
        public string Absence { get; private set; } = "le monde n'a pas encore répondu";
        public int Lectures { get; private set; } // les lectures recueillies
        public bool RequeteEnVol => tache != null && !tache.IsCompleted;
        public DevisDeLaCaserne(int port) { this.port = port; }

        // Recueille la lecture finie, puis en lance une si la période est passée et qu'aucune n'est en vol. Vrai s'il a recueilli.
        public bool Pas(double maintenant)
        {
            bool recueillie = false;
            if (tache != null && tache.IsCompleted) { var lu = tache.Result; (Devis, Absence) = (lu.Devis, lu.Absence); tache = null; Lectures++; recueillie = true; }
            if (tache == null && maintenant >= prochaine) { prochaine = maintenant + PERIODE_S; int p = port; tache = Task.Run(() => Lire(p)); }
            return recueillie;
        }

        // Après un dépôt, la prochaine lecture part au pas suivant, sans attendre la période.
        public void Relire() => prochaine = double.NegativeInfinity;

        static Lu Lire(int port)
        {
            try
            {
                string maison;
                using (var monde = new ClientMonde(port, Delai))
                {
                    var lu = monde.LireAvecMaison();
                    if (!lu.Presente) return new Lu { Absence = lu.Absence };
                    if ((maison = lu.Donnees.MaisonDuJoueur) == null) return new Lu { Absence = "aucune maison choisie" };
                }
                using (var guerre = new ClientGuerre(port, Delai))
                {
                    var lu = guerre.LireOrdres(maison, null);
                    if (!lu.Presente) return new Lu { Absence = lu.Absence };
                    return lu.Donnees.Levee.Batiment == null ? new Lu { Absence = "la capitale est hors de la carte" } : new Lu { Devis = lu.Donnees.Levee.Batiment };
                }
            }
            catch (Exception e) { return new Lu { Absence = "devis : " + e.GetBaseException().Message }; }
        }
    }
}
