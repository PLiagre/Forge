using System;
using System.Collections;
using System.Threading;
using System.Threading.Tasks;
using NUnit.Framework;
using UnityEngine.TestTools;
using Victoria.CityMode.Integration;

namespace Victoria.CityMode.Presentation.PlayModeTests
{
    public sealed class CityModeTransitionPlayModeTests
    {
        CityModeTransitionShell shell;

        [TearDown]
        public void TearDown()
        {
            shell?.Dispose();
            shell = null;
        }

        [UnityTest]
        public IEnumerator SuccessAndReturnRestoreMapContext()
        {
            var host = new FakeHost();
            var gateway = new FakeGateway();
            shell = new CityModeTransitionShell(host);
            CityModeTransitionResult entered = null;
            yield return Await(shell.EnterAsync(Context(), gateway, gateway), value => entered = value);
            Assert.IsTrue(entered.Succeeded, entered.Message);
            Assert.AreEqual(CityModeTransitionState.City, shell.State);

            CityModeTransitionResult exited = null;
            yield return Await(shell.ExitAsync(), value => exited = value);
            Assert.IsTrue(exited.Succeeded, exited.Message);
            Assert.AreEqual(CityModeTransitionState.Map, shell.State);
            Assert.AreEqual("cell:play", host.restored.mapCellId);
            Assert.AreEqual("{\"camera\":\"preserved\"}", host.restored.returnViewStateJson);
        }

        [UnityTest]
        public IEnumerator CancellationRestoresMap()
        {
            var host = new FakeHost { block = true };
            var gateway = new FakeGateway();
            shell = new CityModeTransitionShell(host);
            using (var cancellation = new CancellationTokenSource())
            {
                var task = shell.EnterAsync(Context(), gateway, gateway, cancellation.Token);
                cancellation.Cancel();
                CityModeTransitionResult result = null;
                yield return Await(task, value => result = value);
                Assert.IsFalse(result.Succeeded);
                Assert.AreEqual(CityModeErrorCode.Cancelled, result.Error);
            }
            Assert.AreEqual(CityModeTransitionState.Map, shell.State);
            Assert.AreEqual(1, host.restoreCount);
        }

        [UnityTest]
        public IEnumerator FailureIsRecoverableAndRestoresMap()
        {
            var host = new FakeHost { fail = true };
            var gateway = new FakeGateway();
            shell = new CityModeTransitionShell(host);
            CityModeTransitionResult result = null;
            yield return Await(shell.EnterAsync(Context(), gateway, gateway), value => result = value);
            Assert.IsFalse(result.Succeeded);
            Assert.AreEqual(CityModeErrorCode.InternalError, result.Error);
            Assert.AreEqual(CityModeTransitionState.Map, shell.State);
            Assert.AreEqual(1, host.restoreCount);
        }

        [UnityTest]
        public IEnumerator DoubleClickStartsOnlyOneLoad()
        {
            var host = new FakeHost { hold = true };
            var gateway = new FakeGateway();
            shell = new CityModeTransitionShell(host);
            var first = shell.EnterAsync(Context(), gateway, gateway);
            CityModeTransitionResult duplicate = null;
            yield return Await(
                shell.EnterAsync(Context("session:duplicate"), gateway, gateway),
                value => duplicate = value);
            Assert.IsFalse(duplicate.Succeeded);
            Assert.AreEqual(CityModeErrorCode.SessionAlreadyActive, duplicate.Error);
            Assert.AreEqual(1, host.loadCount);

            host.Release();
            CityModeTransitionResult entered = null;
            yield return Await(first, value => entered = value);
            Assert.IsTrue(entered.Succeeded, entered.Message);
            yield return Await(shell.ExitAsync(), _ => { });
        }

        [UnityTest]
        public IEnumerator FiftyTransitionsStayWithinShellBudgets()
        {
            var host = new FakeHost();
            var gateway = new FakeGateway();
            shell = new CityModeTransitionShell(host);
            for (var index = 0; index < 50; index++)
            {
                CityModeTransitionResult entered = null;
                yield return Await(
                    shell.EnterAsync(Context("session:soak:" + index), gateway, gateway),
                    value => entered = value);
                Assert.IsTrue(entered.Succeeded, "enter " + index + ": " + entered.Message);

                CityModeTransitionResult exited = null;
                yield return Await(shell.ExitAsync(), value => exited = value);
                Assert.IsTrue(exited.Succeeded, "exit " + index + ": " + exited.Message);
                yield return null;
            }

            Assert.AreEqual(CityModeTransitionState.Map, shell.State);
            Assert.IsFalse(CityModePresentationHost.HasActiveInstance);
            Assert.AreEqual(50, shell.Metrics.CompletedEntries);
            Assert.AreEqual(50, shell.Metrics.CompletedReturns);
            Assert.Less(shell.Metrics.MaximumEntryMilliseconds, 3000d);
            Assert.Less(shell.Metrics.MaximumReturnMilliseconds, 5000d);
        }

        static IEnumerator Await<T>(Task<T> task, Action<T> complete)
        {
            while (!task.IsCompleted)
                yield return null;
            if (task.IsFaulted)
                throw task.Exception ?? new Exception("Transition task faulted.");
            if (task.IsCanceled)
                throw new OperationCanceledException();
            complete(task.Result);
        }

        static CityLaunchContext Context(string sessionId = "session:play")
        {
            return new CityLaunchContext
            {
                sessionId = sessionId,
                cityId = "city:play",
                mapCellId = "cell:play",
                worldSeed = 99,
                worldTick = 400,
                stateRevision = 12,
                timePolicy = CityWorldTimePolicy.PauseWorld,
                worldTimeScalePermille = 0,
                returnViewId = "map:main",
                returnViewStateJson = "{\"camera\":\"preserved\"}"
            };
        }

        sealed class FakeHost : ICityModeTransitionHost
        {
            readonly TaskCompletionSource<bool> release = new TaskCompletionSource<bool>();
            public bool block;
            public bool hold;
            public bool fail;
            public int loadCount;
            public int restoreCount;
            public CityLaunchContext restored;

            public async Task<ICityModePresentationView> LoadCityAsync(
                CityLaunchContext context,
                IProgress<float> progress,
                CancellationToken cancellationToken)
            {
                loadCount++;
                progress.Report(0.5f);
                if (fail)
                    throw new InvalidOperationException("synthetic player load failure");
                if (block)
                    await Task.Delay(Timeout.Infinite, cancellationToken);
                if (hold)
                {
                    using (cancellationToken.Register(() => release.TrySetCanceled()))
                        await release.Task;
                }
                return new RecordingView();
            }

            public Task UnloadCityAsync(
                CityLaunchContext context,
                CancellationToken cancellationToken)
            {
                return Task.CompletedTask;
            }

            public Task RestoreMapAsync(
                CityLaunchContext context,
                CancellationToken cancellationToken)
            {
                restoreCount++;
                restored = context;
                return Task.CompletedTask;
            }

            public void Release()
            {
                release.TrySetResult(true);
            }
        }

        sealed class RecordingView : ICityModePresentationView
        {
            public void Open(CityLaunchContext context)
            {
            }

            public void Present(CitySnapshotEnvelope snapshot)
            {
            }

            public void CompleteIntent(CityIntentReceipt receipt)
            {
            }

            public void Close()
            {
            }
        }

        sealed class FakeGateway : ICityModeSnapshotSource, ICityModeIntentSink
        {
            public CitySnapshotEnvelope ReadSnapshot(CityLaunchContext context)
            {
                return new CitySnapshotEnvelope
                {
                    cityId = context.cityId,
                    worldTick = context.worldTick,
                    stateRevision = context.stateRevision,
                    isFullSnapshot = true,
                    payloadJson = "{}",
                    payloadSha256 = new string('d', 64)
                };
            }

            public CityIntentReceipt SubmitIntent(CityIntentEnvelope intent)
            {
                return new CityIntentReceipt
                {
                    sessionId = intent.sessionId,
                    intentId = intent.intentId,
                    cityId = intent.cityId,
                    status = CityIntentStatus.Accepted,
                    errorCode = CityModeErrorCode.None,
                    resultingWorldTick = intent.issuedAtWorldTick,
                    resultingStateRevision = intent.expectedStateRevision
                };
            }
        }
    }
}
