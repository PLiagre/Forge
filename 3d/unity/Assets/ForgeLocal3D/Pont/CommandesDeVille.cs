using System;
using System.Threading;
using System.Threading.Tasks;

namespace Forge.Pont {
    // Lot #730 : depuis la ville, C revient à la carte et Espace suspend ou reprend le temps.
    // La reprise prend la vitesse de ville lue dans la ressource. Le service tient seul les ticks : les requêtes partent
    // hors du fil principal. Une lecture en vol est annulée ; un POST déjà parti n'est jamais coupé, le retour attend sa réponse.
    public sealed class CommandesDeVille {
        static readonly TimeSpan Delai = TimeSpan.FromSeconds(2);
        readonly int port; CancellationTokenSource arret; Task tache;
        public string Absence { get; private set; }
        public double? VitessePosee { get; private set; }
        public bool RequeteEnVol => tache != null && !tache.IsCompleted;
        public bool RetourDemande { get; private set; } // C pendant une pause en vol : à redemander jusqu'à sa fin
        public CommandesDeVille(int port) { this.port = port; }

        public bool Basculer() {
            if (RequeteEnVol) return false;
            int p = port; double ville = ReglagesDesVues.Charger().VitesseVille; CancellationToken jeton = (arret = new CancellationTokenSource()).Token;
            (VitessePosee, Absence) = (null, null);
            tache = Task.Run(() => { try { using (var client = new ClientHorloge(p, Delai)) {
                Lecture<HorlogeLue> lue; using (jeton.Register(client.Dispose)) lue = client.Lire();
                if (!lue.Presente || jeton.IsCancellationRequested) { Noter(null, lue.Absence ?? "horloge : pause annulée, vitesse non envoyée"); return; }
                var reglee = client.Regler(lue.Donnees.JoursParSeconde > 0 ? 0 : ville); Noter(reglee.Donnees?.JoursParSeconde, reglee.Absence);
            } } catch (Exception e) { Noter(null, "horloge : " + e.GetBaseException().Message); } });
            return true;
        }

        // Pause en vol : rien ne part, le service a fini d'appliquer son POST avant que la transition ne lise l'horloge.
        public TransitionDeVue Retour() {
            arret?.Cancel(); if (RetourDemande = RequeteEnVol) return null;
            return TransitionDeVue.Lancer(OuvertureDeLaCarte.SCENE, VueDuJeu.Carte, port);
        }
        void Noter(double? posee, string absence) => (VitessePosee, Absence) = (posee, absence);
    }
}
