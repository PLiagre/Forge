using System;
using System.Collections;
using System.Globalization;
using Forge.Pont;
using UnityEngine;

namespace ForgeLocal3D.Captures
{
    // Lot 525 : la date et l'horloge sur la carte. La capture lance le service en pause, au tick 30 ; la carte s'ouvre comme
    // au lot 549, ses touches en automatique. Le scénario fait ce que le joueur ferait : deux fois « plus vite » (de la pause,
    // 0,5 puis 1 jour par seconde), puis il attend que le panneau montre deux ticks de plus, lus au service. Photo : la carte
    // et son horloge en marche. Puis « pause » : le service rend 0 jour par seconde, et le tick ne bouge plus pendant 1,5 s.
    // Photo : la même carte, en pause. Chaque nombre du panneau est celui que `/horloge` a rendu.
    static class Lot525
    {
        const double ATTENTE_S = 20, IMMOBILE_S = 1.5;
        const int IMAGES_DE_POSE = 10;
        static HorlogeDeCarte horloge;

        static string N(double v) => v.ToString("R", CultureInfo.InvariantCulture);

        [ScenarioDeCapture(525, "horloge-en-marche")]
        static IEnumerator EnMarche(Camera camera)
        {
            horloge = null;
            var ouverte = new Lot549.CarteOuverte();
            for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            var carte = ouverte.Carte;
            var h = carte.GetComponent<HorlogeDeCarte>() ?? throw new InvalidOperationException("la carte n'a pas d'horloge");
            (carte.GetComponent<CommandesDuTemps>() ?? throw new InvalidOperationException("la carte n'a pas de commandes du temps")).automatique = true;
            for (var e = Attendre(h, () => h.Lue != null, "une horloge servie"); e.MoveNext();) yield return null;
            if (h.Lue.JoursParSeconde != 0) throw new InvalidOperationException("la capture lance le monde en pause, l'horloge dit " + N(h.Lue.JoursParSeconde));
            if (h.TexteAffiche != HorlogeDeCarte.Decrire(h.Lue)) throw new InvalidOperationException("le panneau dit « " + h.TexteAffiche + " »");

            h.Accelerer();
            for (var e = Attendre(h, () => h.Lue.JoursParSeconde == HorlogeDeCarte.PALIERS[0], "le premier palier"); e.MoveNext();) yield return null;
            h.Accelerer();
            double attendue = HorlogeDeCarte.Suivante(HorlogeDeCarte.PALIERS[0], +1);
            for (var e = Attendre(h, () => h.Lue.JoursParSeconde == attendue, N(attendue) + " jour par seconde"); e.MoveNext();) yield return null;
            long depart = h.Lue.Tick;
            for (var e = Attendre(h, () => h.Lue.Tick >= depart + 2, "deux ticks de plus que " + depart); e.MoveNext();) yield return null;
            if (h.TexteAffiche != HorlogeDeCarte.Decrire(h.Lue)) throw new InvalidOperationException("le panneau dit « " + h.TexteAffiche + " »");

            Lot549.Photographier(camera, carte);
            horloge = h;
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            Debug.Log("CAPTURE_525 en marche : " + h.TexteAffiche.Replace("\n", " | "));
        }

        [ScenarioDeCapture(525, "horloge-en-pause")]
        static IEnumerator EnPause(Camera camera)
        {
            var h = horloge ?? throw new InvalidOperationException("l'horloge n'a pas été mise en marche : « horloge-en-marche » passe avant");
            h.Basculer();
            for (var e = Attendre(h, () => h.Lue.JoursParSeconde == 0, "la pause"); e.MoveNext();) yield return null;
            long arret = h.Lue.Tick;
            double fin = Time.realtimeSinceStartupAsDouble + IMMOBILE_S;
            while (Time.realtimeSinceStartupAsDouble < fin)
            {
                if (h.Lue.Tick != arret) throw new InvalidOperationException("en pause, le tick passe de " + arret + " à " + h.Lue.Tick);
                yield return null;
            }
            if (h.TexteAffiche != HorlogeDeCarte.Decrire(h.Lue) || !h.TexteAffiche.EndsWith("En pause", StringComparison.Ordinal))
                throw new InvalidOperationException("le panneau ne dit pas la pause : « " + h.TexteAffiche + " »");
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            Debug.Log("CAPTURE_525 en pause : " + h.TexteAffiche.Replace("\n", " | "));
        }

        static IEnumerator Attendre(HorlogeDeCarte h, Func<bool> condition, string quoi)
        {
            double fin = Time.realtimeSinceStartupAsDouble + ATTENTE_S;
            while (!condition())
            {
                if (Time.realtimeSinceStartupAsDouble > fin)
                    throw new InvalidOperationException("pas de " + quoi + " en " + ATTENTE_S + " s : « " + h.TexteAffiche + " »" + (h.Absence != null ? " (" + h.Absence + ")" : ""));
                yield return null;
            }
        }
    }
}
