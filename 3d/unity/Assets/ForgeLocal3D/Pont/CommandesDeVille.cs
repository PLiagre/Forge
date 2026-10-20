using System;
using System.Threading;
using System.Threading.Tasks;

namespace Forge.Pont {
    // Lot #730 : depuis la ville, C revient à la carte et Espace suspend ou reprend le temps.
    // La reprise prend la vitesse de ville lue dans la ressource. Le service tient seul les ticks :
    // les requêtes partent hors du fil principal, et une pause en vol est annulée avant le retour.
    public sealed class CommandesDeVille {
        static readonly TimeSpan Delai = TimeSpan.FromSeconds(2);
        readonly int port; CancellationTokenSource arret; Task tache;
        public string Absence { get; private set; }
        public double? VitessePosee { get; private set; }
        public bool RequeteEnVol => tache != null && !tache.IsCompleted;
        public CommandesDeVille(int port) { this.port = port; }

        public bool Basculer() {
            if (RequeteEnVol) return false;
            (VitessePosee, Absence) = (null, null);
            int p = port; double ville = ReglagesDesVues.Charger().VitesseVille;
            CancellationToken jeton = (arret = new CancellationTokenSource()).Token;
            tache = Task.Run(() => {
                try {
                    using (var client = new ClientHorloge(p, Delai)) using (jeton.Register(client.Dispose)) {
                        var lue = client.Lire();
                        if (!lue.Presente) { Noter(null, lue.Absence); return; }
                        if (jeton.IsCancellationRequested) { Noter(null, "horloge : pause annulée, vitesse non envoyée"); return; }
                        var reglee = client.Regler(lue.Donnees.JoursParSeconde > 0 ? 0 : ville);
                        if (!reglee.Presente) { Noter(null, reglee.Absence); return; }
                        Noter(reglee.Donnees.JoursParSeconde, null);
                    }
                } catch (Exception e) { Noter(null, "horloge : " + e.GetBaseException().Message); }
            });
            return true;
        }

        public void Annuler() => arret?.Cancel();
        public TransitionDeVue Retour() { Annuler(); return TransitionDeVue.Lancer(OuvertureDeLaCarte.SCENE, VueDuJeu.Carte, port); }
        void Noter(double? posee, string absence) => (VitessePosee, Absence) = (posee, absence);
    }
}
