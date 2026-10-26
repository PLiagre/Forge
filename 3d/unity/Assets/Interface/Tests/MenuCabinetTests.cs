using System.Collections;
using System.Linq;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using UnityEngine.TestTools;

namespace Forge.Interface.Tests
{
    public sealed class MenuCabinetTests
    {
        [UnityTest] public IEnumerator Le_menu_se_ferme_en_rendant_le_focus_sans_dupliquer_le_panneau()
        {
            UnityEditor.SceneManagement.EditorSceneManager.NewScene(UnityEditor.SceneManagement.NewSceneSetup.EmptyScene);
            yield return new EnterPlayMode();
            var parent = new GameObject("preuve", typeof(RectTransform), typeof(EventSystem));
            try
            {
                var avant = new GameObject("sélection", typeof(RectTransform), typeof(Button)); avant.transform.SetParent(parent.transform);
                EventSystem.current.SetSelectedGameObject(avant);
                var menu = parent.AddComponent<MenuCabinet>(); menu.Initialiser(parent.transform);
                menu.Ouvrir(); menu.Ouvrir();
                Assert.IsTrue(menu.Ouvert);
                Assert.AreEqual(1, parent.GetComponentsInChildren<Image>().Count(i => i.name == "Menu du cabinet"));
                Assert.AreEqual("Revenir au jeu", EventSystem.current.currentSelectedGameObject.name);
                menu.Parcourir(false); Assert.AreEqual("Volume", EventSystem.current.currentSelectedGameObject.name);
                menu.Parcourir(true); Assert.AreEqual("Revenir au jeu", EventSystem.current.currentSelectedGameObject.name);
                menu.Fermer(); Assert.IsFalse(menu.Ouvert);
                Assert.AreEqual(avant, EventSystem.current.currentSelectedGameObject);
            }
            finally { Object.DestroyImmediate(parent); }
            yield return new ExitPlayMode();
        }
        [Test] public void Le_reglage_sonore_modifie_le_volume_et_peut_rendre_le_jeu_silencieux()
        {
            var parent = new GameObject("preuve", typeof(RectTransform)); float ancien = AudioListener.volume;
            try
            {
                var menu = parent.AddComponent<MenuCabinet>(); menu.Initialiser(parent.transform); menu.Ouvrir();
                var volume = parent.GetComponentInChildren<Slider>(); Assert.NotNull(volume);
                volume.value = .4f; Assert.AreEqual(.4f, AudioListener.volume, .001f);
                volume.value = 0; Assert.AreEqual(0, AudioListener.volume);
            }
            finally { AudioListener.volume = ancien; Object.DestroyImmediate(parent); }
        }
    }
}
