using System;
using System.Collections.Generic;
using System.Globalization;

namespace Forge.Pont
{
    // Lot #958 — le résumé d'une série de temps d'image (en millisecondes) : médiane, 95e centile et maximum.
    // Le 95e centile se prend au rang le plus proche, k = ⌈95·n/100⌉ : c'est une image vraiment mesurée,
    // jamais une valeur interpolée entre deux images. Le rang se calcule en entiers : `0.95 * n` en double
    // donne 95,00000000000001 pour certains n, et son plafond tomberait un rang trop haut.
    public sealed class ResumeDesTempsDImage
    {
        public int Nombre { get; }
        public double MedianeMs { get; }
        public double P95Ms { get; }
        public double MaximumMs { get; }

        public ResumeDesTempsDImage(int nombre, double medianeMs, double p95Ms, double maximumMs)
        {
            Nombre = nombre;
            MedianeMs = medianeMs;
            P95Ms = p95Ms;
            MaximumMs = maximumMs;
        }
    }

    public static class TempsDImage
    {
        public static ResumeDesTempsDImage Resumer(IReadOnlyList<double> tempsMs)
        {
            if (tempsMs == null) throw new ArgumentNullException(nameof(tempsMs));
            int n = tempsMs.Count;
            if (n == 0) throw new ArgumentException("échantillon vide : aucun temps d'image à résumer", nameof(tempsMs));
            var tri = new double[n];
            for (int i = 0; i < n; i++)
            {
                double t = tempsMs[i];
                if (double.IsNaN(t) || double.IsInfinity(t) || t < 0)
                    throw new ArgumentOutOfRangeException(nameof(tempsMs), "temps d'image au rang " + i + " : " + t.ToString("R", CultureInfo.InvariantCulture) + " (attendu : fini et ≥ 0)");
                tri[i] = t;
            }
            // Une copie triée : la liste reçue n'est jamais modifiée.
            Array.Sort(tri);
            double mediane = n % 2 == 1 ? tri[n / 2] : (tri[n / 2 - 1] + tri[n / 2]) / 2;
            int k = (95 * n + 99) / 100;
            return new ResumeDesTempsDImage(n, mediane, tri[k - 1], tri[n - 1]);
        }
    }
}
