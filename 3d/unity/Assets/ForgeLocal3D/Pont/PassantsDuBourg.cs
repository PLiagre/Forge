using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Linq;
using System.Numerics;

namespace Forge.Pont
{
    // Combien de passants montrer dans le bourg, et de quels métiers : une échelle d'affichage,
    // un passant pour dix habitants du lieu de rang 0. Rien n'est écrit dans le monde, le reliquat
    // sous dix reste des habitants ; chaque appel ne lit que son argument, sans aucune mémoire.
    // Présente : nombre et parts mesurés. Absente : la cause nommée, ni nombre ni parts.
    public sealed class PassantsDuBourg
    {
        public const int HABITANTS_PAR_PASSANT = 10;
        private const long MAX_EXACT = 9007199254740991; // 2^53 − 1
        private const string PAYSANS = "paysans";

        public string Absence { get; }
        public long? Nombre { get; }
        public IReadOnlyDictionary<string, long> ParMetier { get; }
        public bool Presente => Absence == null;

        private PassantsDuBourg(long nombre, Dictionary<string, long> parMetier)
        { Nombre = nombre; ParMetier = new ReadOnlyDictionary<string, long>(parMetier); }

        private PassantsDuBourg(string absence) { Absence = absence; }

        public static PassantsDuBourg Projeter(LectureLieu lecture)
        {
            if (lecture == null) return new PassantsDuBourg("lecture nulle");
            if (!lecture.Presente) return new PassantsDuBourg("lieu absent : " + lecture.Absence);
            Lieu lieu = lecture.Lieu;
            if (lieu.Lieux == null) return new PassantsDuBourg("lieux absents : " + (lieu.AbsenceDesLieux ?? "liste non fournie"));
            LieuPlace bourg = lieu.Bourg;
            if (bourg == null) return new PassantsDuBourg("aucun lieu de rang 0 parmi " + lieu.Lieux.Count + " lieux");
            if (bourg.Population == null) return new PassantsDuBourg("population du bourg absente : " + bourg.AbsenceDePopulation);
            long p = bourg.Population.Value;
            if (p < 0 || p > MAX_EXACT)
                return new PassantsDuBourg("population du bourg hors de 0..2^53 − 1 : " + p.ToString(CultureInfo.InvariantCulture));
            // Un bourg connu vide est un zéro mesuré : ses métiers ne sont pas nécessaires.
            if (p == 0) return new PassantsDuBourg(0, new Dictionary<string, long>());

            if (lieu.EtatFoyers == EtatFoyers.Absents) return new PassantsDuBourg("métiers absents pour un bourg de " + p + " habitants");
            if (lieu.EtatFoyers == EtatFoyers.NonCalcules) return new PassantsDuBourg("métiers non calculés (-1) pour un bourg de " + p + " habitants");
            BigInteger somme = 0, nonPaysans = 0;
            foreach (var metier in lieu.Foyers)
            {
                if (string.IsNullOrWhiteSpace(metier.Key)) return new PassantsDuBourg("nom de métier blanc");
                if (metier.Value.Personnes < 0)
                    return new PassantsDuBourg("compte négatif pour " + metier.Key + " : " + metier.Value.Personnes);
                somme += metier.Value.Personnes;
                if (metier.Key != PAYSANS) nonPaysans += metier.Value.Personnes;
            }
            if (somme != lieu.Population)
                return new PassantsDuBourg("somme des métiers " + somme + " ≠ population de la cellule " + lieu.Population);
            if (p > lieu.Population)
                return new PassantsDuBourg("le bourg (" + p + ") dépasse la cellule (" + lieu.Population + ")");

            // Poids visuels : chaque non-paysan garde ses personnes ; les paysans, ce qui reste du
            // bourg une fois les autres comptés, comme les bras aux champs. Les poids nuls tombent.
            var poids = new SortedDictionary<string, BigInteger>(StringComparer.Ordinal);
            foreach (var metier in lieu.Foyers)
                if (metier.Key != PAYSANS && metier.Value.Personnes > 0) poids.Add(metier.Key, metier.Value.Personnes);
            BigInteger paysans = BigInteger.Max(0, p - nonPaysans);
            if (paysans > 0) poids.Add(PAYSANS, paysans);

            // Plus grands restes, puis le nom ordinal : la somme vaut exactement N, quel que soit l'ordre reçu.
            long n = p / HABITANTS_PAR_PASSANT;
            BigInteger total = poids.Values.Aggregate(BigInteger.Zero, (a, b) => a + b);
            var parts = new Dictionary<string, long>();
            var restes = new List<(string Nom, BigInteger Reste)>();
            long attribues = 0;
            foreach (var metier in poids)
            {
                BigInteger quotient = BigInteger.DivRem(n * metier.Value, total, out BigInteger reste);
                parts.Add(metier.Key, (long)quotient);
                attribues += (long)quotient;
                restes.Add((metier.Key, reste));
            }
            foreach (var plusGrand in restes.OrderByDescending(r => r.Reste).ThenBy(r => r.Nom, StringComparer.Ordinal).Take((int)(n - attribues)))
                parts[plusGrand.Nom] += 1;
            return new PassantsDuBourg(n, parts);
        }
    }
}
