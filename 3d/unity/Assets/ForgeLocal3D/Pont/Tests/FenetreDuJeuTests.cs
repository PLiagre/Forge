using NUnit.Framework;
using UnityEngine;

namespace Forge.Pont.Tests {
    // Une fenêtre à la taille de l'écran ne tient pas dans l'écran une fois sa barre de titre posée : elle passe en plein
    // écran fenêtré. Une fenêtre plus petite, ou un plein écran déjà demandé, ne change pas.
    public sealed class FenetreDuJeuTests {
        [Test] public void Une_fenetre_a_la_taille_de_l_ecran_deborde_une_plus_petite_non() {
            Assert.IsTrue(FenetreDuJeu.Deborde(1920, 1080, 1920, 1080, FullScreenMode.Windowed), "la fenêtre de 1920 × 1080 sur un écran de 1920 × 1080 tient");
            Assert.IsTrue(FenetreDuJeu.Deborde(1920, 1200, 2560, 1080, FullScreenMode.Windowed), "trop haute seulement");
            Assert.IsTrue(FenetreDuJeu.Deborde(2560, 900, 1920, 1080, FullScreenMode.Windowed), "trop large seulement");
            Assert.IsFalse(FenetreDuJeu.Deborde(1600, 900, 1920, 1080, FullScreenMode.Windowed), "une fenêtre plus petite que l'écran déborde");
            foreach (var mode in new[] { FullScreenMode.FullScreenWindow, FullScreenMode.ExclusiveFullScreen, FullScreenMode.MaximizedWindow })
                Assert.IsFalse(FenetreDuJeu.Deborde(1920, 1080, 1920, 1080, mode), mode + " : un plein écran déjà demandé est changé");
            Assert.IsFalse(FenetreDuJeu.Deborde(1920, 1080, 0, 0, FullScreenMode.Windowed), "un écran inconnu fait changer la fenêtre");
        }
    }
}
