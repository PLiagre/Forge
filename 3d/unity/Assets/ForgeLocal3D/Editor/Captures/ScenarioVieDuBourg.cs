using System.Collections;using UnityEngine;
namespace ForgeLocal3D.Captures
{
    // La même place de Biskra nourrie puis affamée, déroulée par la session commune (EpreuveVieDuBourg), même caméra, 19,6 h.
    // 01 : vraies maisons, fumées et lampes, comptoir garni ; 02 : le panier vidé une fois par le service d'épreuve, denrées et fumées parties, lampes gardées.
    static class ScenarioVieDuBourg
    {
        [ScenarioDeCapture("vie-du-bourg","01-place-nourrie")]static IEnumerator PlaceNourrie(Camera camera)=>EpreuveVieDuBourg.Nourrie(camera);
        [ScenarioDeCapture("vie-du-bourg","02-place-affamee")]static IEnumerator PlaceAffamee(Camera camera)=>EpreuveVieDuBourg.Affamee(camera);
    }
}
