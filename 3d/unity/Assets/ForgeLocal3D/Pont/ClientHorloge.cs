using System;
using System.Collections.Generic;
using System.Globalization;
using System.Net.Http;

namespace Forge.Pont
{
    // L'horloge telle que le service la tient : le tick, la date et la vitesse en jours par seconde (0 : en pause).
    // Les mesures de diagnostic (`duree_dernier_tick_ms`, `budget_tick_ms`) ne sont pas relues.
    public sealed class HorlogeLue
    {
        public long Tick { get; }
        public DateDuMonde Date { get; }
        public double JoursParSeconde { get; }
        public HorlogeLue(long tick, DateDuMonde date, double joursParSeconde) { Tick = tick; Date = date; JoursParSeconde = joursParSeconde; }
    }

    // Lit (`GET /horloge`) et règle (`POST /vitesse`) l'horloge du service local. Le service tient seul le temps :
    // Unity transmet une vitesse et relit celle que le service rend, sans jamais avancer le monde lui-même.
    public sealed class ClientHorloge : IDisposable
    {
        private readonly ServiceLocal service;

        public ClientHorloge(int port, TimeSpan delai) { service = new ServiceLocal(port, delai, "horloge : "); }

        public void Dispose() => service.Dispose();

        public Lecture<HorlogeLue> Lire() => service.Demander(HttpMethod.Get, "/horloge", Horloge);

        // 0 met le monde en pause. Une vitesse négative, NaN ou infinie lève avant tout envoi.
        public Lecture<HorlogeLue> Regler(double joursParSeconde)
        {
            if (!(joursParSeconde >= 0) || double.IsInfinity(joursParSeconde))
                throw new ArgumentOutOfRangeException(nameof(joursParSeconde), joursParSeconde, "une vitesse finie ≥ 0 attendue");
            // « R » en culture invariante écrit 2.5, jamais 2,5 ; l'échappement garde le + de 1E+20, qu'une requête lirait comme une espace.
            string vitesse = Uri.EscapeDataString(joursParSeconde.ToString("R", CultureInfo.InvariantCulture));
            return service.Demander(HttpMethod.Post, "/vitesse?jours_par_seconde=" + vitesse, Horloge);
        }

        private static HorlogeLue Horloge(Dictionary<string, object> racine)
        {
            double vitesse = ServiceLocal.Nombre(ServiceLocal.Valeur(racine, "jours_par_seconde"), "jours_par_seconde");
            if (vitesse < 0) throw ServiceLocal.Refus("jours_par_seconde", "un nombre ≥ 0", vitesse);
            return new HorlogeLue(ServiceLocal.Entier(racine, "tick", 0), ServiceLocal.Date(racine), vitesse);
        }
    }
}
