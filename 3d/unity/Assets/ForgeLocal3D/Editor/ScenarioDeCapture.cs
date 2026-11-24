using System;
using System.Text.RegularExpressions;

namespace ForgeLocal3D
{
    // Un scénario de capture : ce qu'on pose ou joue dans la scène avant une photo. Le plan fixe
    // (la caméra de la scène, sans rien toucher) ne montre ni un bâtiment du kit qu'on n'a pas posé,
    // ni une route qu'on n'a pas tracée, ni une caméra qui bouge.
    //
    // Un scénario est une méthode statique d'un script d'éditeur, de la forme
    //     [ScenarioDeCapture("route", "tracee")]
    //     static IEnumerator Jouer(Camera camera) { … yield return null; … }
    // Son groupe dit ce qu'il montre. La capture (`Capture.Photographier`, avec `-forgeScenario route`)
    // prend d'abord le plan fixe, puis joue
    // chaque scénario du groupe dans l'ordre de leur nom : `yield return null` laisse passer une image,
    // et quand le scénario a fini, la caméra qu'il a reçue (déplacée ou non) est photographiée sous
    // `<scène>--<nom>.png`. Exemple : `Captures/ScenarioExemple.cs`.
    // Un `yield return` d'un autre IEnumerator ne l'exécute pas (ce n'est pas une coroutine) : pour
    // attendre plusieurs images, `for (…) yield return null;`. La caméra de la ville se pose par
    // `DesertCityCamera.Poser` ; bouger `camera.transform` à la main, elle le reprend à l'image suivante.
    // Un scénario qui charge une autre scène (la carte) fait `yield return` de la caméra de cette scène : c'est elle que la
    // capture photographie désormais, pour ce scénario et les suivants du groupe.
    [AttributeUsage(AttributeTargets.Method, AllowMultiple = false)]
    public sealed class ScenarioDeCaptureAttribute : Attribute
    {
        static readonly Regex NomPermis = new Regex("^[a-z0-9]+(-[a-z0-9]+)*$");

        public string Groupe { get; }
        public string Nom { get; }
        // La taille de la photo, en pixels : 1600 × 900 sauf si le scénario en demande une autre (`Largeur = 1920, Hauteur = 1080`).
        public int Largeur { get; set; } = 1600;
        public int Hauteur { get; set; } = 900;

        public ScenarioDeCaptureAttribute(string groupe, string nom)
        {
            Groupe = groupe;
            Nom = nom;
        }

        // null si le scénario est bien formé, sinon ce qui ne va pas.
        public string Defaut()
        {
            if (Groupe == null || !NomPermis.IsMatch(Groupe)) return "groupe « " + Groupe + " » : minuscules, chiffres et tirets seulement";
            if (Nom == null || !NomPermis.IsMatch(Nom)) return "nom « " + Nom + " » : minuscules, chiffres et tirets seulement";
            if (Largeur < 16 || Hauteur < 16 || Largeur > 7680 || Hauteur > 4320) return "photo de " + Largeur + " × " + Hauteur + " : de 16 à 7680 × 4320";
            return null;
        }
    }
}
