using System;
using System.Text.RegularExpressions;

namespace ForgeLocal3D
{
    // Un scénario de capture : ce qu'un lot pose ou joue dans la scène avant sa photo. Le plan fixe
    // (la caméra de la scène, sans rien toucher) ne montre ni un bâtiment du kit qu'on n'a pas posé,
    // ni une route qu'on n'a pas tracée, ni une caméra qui bouge : du 30 septembre au 3 octobre 2026,
    // treize captures de lots Unity étaient identiques à l'octet près.
    //
    // Un scénario est une méthode statique d'un script d'éditeur, de la forme
    //     [ScenarioDeCapture(235, "route-tracee")]
    //     static IEnumerator Jouer(Camera camera) { … yield return null; … }
    // La capture (`Capture.Photographier`, avec `-forgeLot 235`) prend d'abord le plan fixe, puis joue
    // chaque scénario du lot dans l'ordre de leur nom : `yield return null` laisse passer une image,
    // et quand le scénario a fini, la caméra qu'il a reçue (déplacée ou non) est photographiée sous
    // `<scène>--<nom>.png`. Exemple : `Captures/ScenarioExemple.cs`.
    [AttributeUsage(AttributeTargets.Method, AllowMultiple = false)]
    public sealed class ScenarioDeCaptureAttribute : Attribute
    {
        static readonly Regex NomPermis = new Regex("^[a-z0-9]+(-[a-z0-9]+)*$");

        public int Lot { get; }
        public string Nom { get; }

        public ScenarioDeCaptureAttribute(int lot, string nom)
        {
            Lot = lot;
            Nom = nom;
        }

        // null si le scénario est bien formé, sinon ce qui ne va pas.
        public string Defaut()
        {
            if (Lot < 0) return "numéro de lot négatif : " + Lot;
            if (Nom == null || !NomPermis.IsMatch(Nom)) return "nom « " + Nom + " » : minuscules, chiffres et tirets seulement";
            return null;
        }
    }
}
