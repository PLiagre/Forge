using System.IO;
using System.Linq;
using System.Reflection;
using NUnit.Framework;
using UnityEngine;

namespace Victoria.CityMode.Tests
{
    public sealed class CityLabBootstrapTests
    {
        [Test]
        public void Bootstrap_HasNoAutomaticRuntimeInitializer()
        {
            var methods = typeof(CityLabBootstrap).GetMethods(
                BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static);
            Assert.IsFalse(methods.Any(method => method
                .GetCustomAttributes(typeof(RuntimeInitializeOnLoadMethodAttribute), false)
                .Any()));
            Assert.IsNotNull(typeof(CityLabBootstrap).GetMethod(
                "StartLaboratory", BindingFlags.Public | BindingFlags.Static));
        }

        [Test]
        public void LaboratoryScene_OwnsItsGameExplicitly()
        {
            const string scenePath = "Assets/CityLabHost/Scenes/CityLab.unity";
            const string gameScriptPath =
                "Packages/com.victoria.citymode/Runtime/CityLabGame.cs";
            var scriptGuid = UnityEditor.AssetDatabase.AssetPathToGUID(gameScriptPath);
            Assert.IsFalse(string.IsNullOrEmpty(scriptGuid));
            var scene = File.ReadAllText(scenePath);
            StringAssert.Contains("guid: " + scriptGuid, scene);
        }
    }
}
