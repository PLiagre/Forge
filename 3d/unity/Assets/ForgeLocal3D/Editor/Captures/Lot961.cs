using System.Collections;
using UnityEngine;
namespace ForgeLocal3D.Captures
{
    // Lot 961 : la ville dense de #959 et ses quatre vues, avec les fumées et les lampes réglées au loin ; le rapport reste `lot959-ville-dense.json`.
    static class Lot961
    {
        [ScenarioDeCapture(961, "1-montage")] static IEnumerator Montage(Camera camera) => Lot959.Montage(camera);
        [ScenarioDeCapture(961, "2-survol")] static IEnumerator Survol(Camera camera) => Lot959.Survol(camera);
        [ScenarioDeCapture(961, "3-rue")] static IEnumerator Rue(Camera camera) => Lot959.Rue(camera);
        [ScenarioDeCapture(961, "4-place")] static IEnumerator Place(Camera camera) => Lot959.Place(camera);
        [ScenarioDeCapture(961, "5-chantier")] static IEnumerator Chantier(Camera camera) => Lot959.Chantier(camera);
    }
}
