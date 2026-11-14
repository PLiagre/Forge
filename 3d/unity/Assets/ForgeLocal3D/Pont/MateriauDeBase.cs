using UnityEngine;
using UnityEngine.Rendering;

namespace Forge.Pont {
    // Le matériau dont se tirent les matériaux créés par le code (rubans des parcelles, chaussées, repères, flèches).
    // Celui du pipeline n'existe que dans l'éditeur : dans un build il est nul, et rien de tout cela ne se dessinait.
    // Le projet embarque donc le sien (`Resources/Forge/Carte`, un matériau éclairé blanc), pris quand l'autre manque.
    public static class MateriauDeBase {
        public const string RESSOURCE = "Forge/Carte";

        public static Material Prendre() {
            RenderPipelineAsset pipeline = GraphicsSettings.currentRenderPipeline;
            Material duPipeline = pipeline != null ? pipeline.defaultMaterial : null;
            return duPipeline != null ? duPipeline : Resources.Load<Material>(RESSOURCE);
        }
    }
}
