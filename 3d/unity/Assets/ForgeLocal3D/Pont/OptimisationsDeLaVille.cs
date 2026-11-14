using System;

namespace Forge.Pont
{
    // L'interrupteur des optimisations de la ville : actives, sauf sous `-forgeSansOptimisations`.
    // Les optimisations de la ville se branchent sur `Actives` ; la contre-épreuve joue sous `-forgeSansOptimisations`.
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
