using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text.RegularExpressions;
using UnityEngine;

namespace Forge.Pont
{
    // Lot #870 — les mots du monde : la date servie, les jours, les masses et les grands nombres s'écrivent partout pareil,
    // comme un clerc tient son registre. Les deux juges refusent un texte qui montre un identifiant ou un nombre sans unité.
    public static class TexteDuMonde
    {
        // Posé à la main : la culture `fr-FR` du système sépare les milliers par U+202F ou U+00A0 selon le runtime.
        private static readonly NumberFormatInfo Fr = NumberFormatInfo.ReadOnly(new NumberFormatInfo {
            NumberDecimalSeparator = ",", NumberGroupSeparator = " ", NumberGroupSizes = new[] { 3 }, NegativeSign = "-" });
        private const string Absent = "déclaré absent par le monde";
        private static readonly Regex MotInterdit = new Regex(@"(?<!\w)(?:cellule|rang|ticks?)(?!\w)", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
        private static readonly Regex IdentifiantDeLieu = new Regex(@"(?<![\p{L}\p{Nd}])[0-9]+-[0-9]+(?![\p{L}\p{Nd}])");
        // Un nombre : ses groupes de trois chiffres d'abord, pour qu'un « 5 631 » ne se coupe jamais en « 5 ».
        private static readonly Regex NombreEcrit = new Regex(@"(?<![\p{L}\p{Nd}])(?:[0-9]{1,3}(?:[   ][0-9]{3})+(?![0-9])|[0-9]+)(?:,[0-9]+)?");
        private static readonly Regex Unite = new Regex(@"\G[  ]?(?:kg|t|%|jours?|ans?|habitants?|foyers?|personnes?|bras|lieux?|maisons?|chantiers?|km|m)(?!\p{L})",
            RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
        private static readonly Regex DateEcrite = new Regex(@"(?<![\p{L}\p{Nd}])jour[  ]([0-9]+)[  ]de[  ]([0-9]+)", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);

        public static string Nombre(long n) => n.ToString("#,0", Fr);

        // La date que le service sert (`ServiceLocal.Date`), jamais calculée ici depuis un tick. L'année s'écrit sans séparateur.
        public static string Date(DateDuMonde d)
        {
            if (d.JourDeLAnnee < 1 || d.JourDeLAnnee > 366) throw new ArgumentOutOfRangeException(nameof(d), "jour de l'année hors de 1…366 : " + d.JourDeLAnnee);
            if (d.Annee < 1) throw new ArgumentOutOfRangeException(nameof(d), "année avant 1 : " + d.Annee);
            return "jour " + d.JourDeLAnnee.ToString(CultureInfo.InvariantCulture) + " de " + d.Annee.ToString(CultureInfo.InvariantCulture);
        }

        public static string Jours(long n) => n < 0 ? throw new ArgumentOutOfRangeException(nameof(n), "durée négative : " + n) : Nombre(n) + (n > 1 ? " jours" : " jour");

        // Sous 1 000 kg (au centième), les kilos ; au-delà, des tonnes à trois chiffres utiles comptés après arrondi.
        public static string Masse(double kg)
        {
            if (double.IsNaN(kg) || double.IsInfinity(kg)) throw new ArgumentException("masse non finie : " + kg, nameof(kg));
            double v = Math.Abs(kg), kilos = Math.Round(v, 2, MidpointRounding.AwayFromZero), t = v / 1000;
            string ecrit;
            if (kilos < 1000) ecrit = kilos.ToString("0.##", Fr) + " kg";
            else if (Math.Round(t, 2, MidpointRounding.AwayFromZero) < 10) ecrit = Math.Round(t, 2, MidpointRounding.AwayFromZero).ToString("0.00", Fr) + " t";
            else if (Math.Round(t, 1, MidpointRounding.AwayFromZero) < 100) ecrit = Math.Round(t, 1, MidpointRounding.AwayFromZero).ToString("0.0", Fr) + " t";
            else ecrit = Math.Round(t, 0, MidpointRounding.AwayFromZero).ToString("#,0", Fr) + " t";
            return kg < 0 && ecrit != "0 kg" ? "-" + ecrit : ecrit; // un reste négatif arrondi à zéro ne s'écrit pas « -0 kg »
        }

        // Le premier mot interdit, au plus petit indice, tel qu'écrit ; `null` si le texte est propre.
        public static string Interdit(string texte, params string[] identifiants)
        {
            if (texte == null) throw new ArgumentNullException(nameof(texte));
            if (identifiants == null) throw new ArgumentNullException(nameof(identifiants));
            if (identifiants.Any(string.IsNullOrWhiteSpace)) throw new ArgumentException("identifiant nul ou blanc", nameof(identifiants));
            IEnumerable<Match> trouves = new[] { MotInterdit.Match(texte), IdentifiantDeLieu.Match(texte) }
                .Concat(identifiants.Select(id => Regex.Match(texte, @"(?<!\w)" + Regex.Escape(id) + @"(?!\w)", RegexOptions.CultureInvariant)));
            return trouves.Where(m => m.Success).OrderBy(m => m.Index).FirstOrDefault()?.Value;
        }

        // Le premier nombre, tel qu'écrit, qui n'a ni unité ni place dans « jour N de AAAA » ; `null` s'il n'y en a pas.
        public static string SansUnite(string texte)
        {
            if (texte == null) throw new ArgumentNullException(nameof(texte));
            var places = new HashSet<(int, int)>(DateEcrite.Matches(texte).Cast<Match>()
                .SelectMany(m => new[] { (m.Groups[1].Index, m.Groups[1].Length), (m.Groups[2].Index, m.Groups[2].Length) }));
            return NombreEcrit.Matches(texte).Cast<Match>()
                .FirstOrDefault(n => !places.Contains((n.Index, n.Length)) && !Unite.Match(texte, n.Index + n.Length).Success)?.Value;
        }

        // Une raison d'absence qui montre un identifiant ou un nombre nu se tait devant le joueur ; le journal la garde.
        public static string Absence(string raison, params string[] identifiants)
        {
            if (raison == null) throw new ArgumentNullException(nameof(raison));
            if (string.IsNullOrWhiteSpace(raison)) throw new ArgumentException("raison d'absence blanche", nameof(raison));
            if (Interdit(raison, identifiants) == null && SansUnite(raison) == null) return raison;
            Debug.Log("TexteDuMonde : absence déclarée par le monde : " + raison);
            return Absent;
        }
    }
}
