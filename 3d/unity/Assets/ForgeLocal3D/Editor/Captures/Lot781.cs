using System.Collections;using UnityEngine;
namespace ForgeLocal3D.Captures
{
    // Lot 781 : la même place de Biskra nourrie puis affamée, déroulée par la session commune (EpreuveVieDuBourg), même caméra, 19,6 h.
    // 01 : vraies maisons, fumées et lampes, comptoir garni ; 02 : le panier vidé une fois par #777, denrées et fumées parties, lampes gardées.
    [Capture.ServiceEpreuve] static class Lot781
    {
        [ScenarioDeCapture(781,"01-place-nourrie")]static IEnumerator PlaceNourrie(Camera camera)=>EpreuveVieDuBourg.Nourrie(camera);
        [ScenarioDeCapture(781,"02-place-affamee")]static IEnumerator PlaceAffamee(Camera camera)=>EpreuveVieDuBourg.Affamee(camera);
    }
}
