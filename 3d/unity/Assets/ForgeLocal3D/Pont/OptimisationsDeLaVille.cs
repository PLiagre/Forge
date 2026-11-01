using System;

namespace Forge.Pont
{
    // Lot #958 — l'interrupteur des optimisations de la ville : actives, sauf sous `-forgeSansOptimisations`.
    // Rien ne le lit encore : les sous-lots 4 et 5 de #422 brancheront leurs optimisations sur `Actives`, et le
    // sous-lot 6 jouera sa contre-épreuve avec `-forgeSansOptimisations`.
    public static class OptimisationsDeLaVille
    {
        public const string SANS = "-forgeSansOptimisations";

        public static readonly bool Actives = Lire(Environment.GetCommandLineArgs());

        // Faux seulement si un argument est exactement SANS, casse comprise.
        public static bool Lire(string[] arguments)
        {
            if (arguments == null) throw new ArgumentNullException(nameof(arguments));
            return Array.IndexOf(arguments, SANS) < 0;
        }
    }
}
