using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using NUnit.Framework;
using Victoria.CityMode.Integration;

namespace Victoria.CityMode.Presentation.Tests
{
    public sealed class CityModeTransitionShellTests
    {
        CityModeTransitionShell shell;

        [TearDown]
        public void TearDown()
        {
            shell?.Dispose();
            shell = null;
        }

        [Test]
        public async Task SuccessPreservesReturnViewportAndSelection()
        {
            var host = new FakeTransitionHost();
            var observer = new RecordingObserver();
            var gateway = new FakeGateway();
            shell = new CityModeTransitionShell(host, observer);

            var entered = await shell.EnterAsync(Context(), gateway, gateway);
            Assert.IsTrue(entered.Succeeded, entered.Message);
            Assert.AreEqual(CityModeTransitionState.City, shell.State);
            Assert.AreEqual(1, host.loadCount);
            Assert.AreEqual("city:42", host.view.openedCityId);
            Assert.AreEqual(9, host.view.presentedRevision);
            CollectionAssert.Contains(observer.states, CityModeTransitionState.LoadingCity);
            CollectionAssert.Contains(observer.progress, 0.5f);

            var exited = await shell.ExitAsync();
            Assert.IsTrue(exited.Succeeded, exited.Message);
            Assert.AreEqual(CityModeTransitionState.Map, shell.State);
            Assert.AreEqual(1, host.unloadCount);
            Assert.AreEqual(1, host.restoreCount);
            Assert.AreEqual("cell:42", host.restoredContext.mapCellId);
            Assert.AreEqual("map:political", host.restoredContext.returnViewId);
            Assert.AreEqual("{\"x\":12,\"y\":34,\"zoom\":2}",
                host.restoredContext.returnViewStateJson);
            Assert.AreEqual(1, host.view.closeCount);
            Assert.AreEqual(1, shell.Metrics.CompletedEntries);
            Assert.AreEqual(1, shell.Metrics.CompletedReturns);
        }

        [Test]
        public async Task CancellationRollsBackAndRestoresMap()
        {
            var host = new FakeTransitionHost { blockLoad = true };
            var gateway = new FakeGateway();
            shell = new CityModeTransitionShell(host);
            using (var cancellation = new CancellationTokenSource())
            {
                var transition = shell.EnterAsync(
                    Context(), gateway, gateway, cancellation.Token);
                await host.loadEntered.Task;
                cancellation.Cancel();

                var result = await transition;
                Assert.IsFalse(result.Succeeded);
                Assert.AreEqual(CityModeErrorCode.Cancelled, result.Error);
            }
            Assert.AreEqual(CityModeTransitionState.Map, shell.State);
            Assert.AreEqual(1, host.unloadCount);
            Assert.AreEqual(1, host.restoreCount);
        }

        [Test]
        public async Task TimeoutRollsBackAndReturnsVersionedError()
        {
            var host = new FakeTransitionHost { blockLoad = true };
            var gateway = new FakeGateway();
            shell = new CityModeTransitionShell(
                host,
                null,
                new CityModeTransitionBudgets(
                    TimeSpan.FromMilliseconds(25),
                    TimeSpan.FromMilliseconds(25),
                    TimeSpan.FromSeconds(1)));

            var result = await shell.EnterAsync(Context(), gateway, gateway);
            Assert.IsFalse(result.Succeeded);
            Assert.AreEqual(CityModeErrorCode.Timeout, result.Error);
            Assert.AreEqual(CityModeTransitionState.Map, shell.State);
            Assert.AreEqual(1, host.unloadCount);
            Assert.AreEqual(1, host.restoreCount);
        }

        [Test]
        public async Task LoadFailureRollsBackAndExposesRecoverableError()
        {
            var host = new FakeTransitionHost { failLoad = true };
            var observer = new RecordingObserver();
            var gateway = new FakeGateway();
            shell = new CityModeTransitionShell(host, observer);

            var result = await shell.EnterAsync(Context(), gateway, gateway);
            Assert.IsFalse(result.Succeeded);
            Assert.AreEqual(CityModeErrorCode.InternalError, result.Error);
            Assert.AreEqual(CityModeTransitionState.Map, shell.State);
            Assert.AreEqual(CityModeErrorCode.InternalError, observer.lastError);
            Assert.AreEqual(1, host.restoreCount);
        }

        [Test]
        public async Task ConcurrentEntryIsRejectedBeforeSecondLoad()
        {
            var host = new FakeTransitionHost { holdLoad = true };
            var gateway = new FakeGateway();
            shell = new CityModeTransitionShell(host);

            var first = shell.EnterAsync(Context(), gateway, gateway);
            await host.loadEntered.Task;
            var duplicate = await shell.EnterAsync(Context("session:duplicate"), gateway, gateway);
            Assert.IsFalse(duplicate.Succeeded);
            Assert.AreEqual(CityModeErrorCode.SessionAlreadyActive, duplicate.Error);
            Assert.AreEqual(1, host.loadCount);

            host.ReleaseLoad();
            Assert.IsTrue((await first).Succeeded);
            Assert.IsTrue((await shell.ExitAsync()).Succeeded);
        }

        [Test]
        public async Task FiftyTransitionsLeaveNoActivePresentationOrSession()
        {
            var host = new FakeTransitionHost();
            var gateway = new FakeGateway();
            shell = new CityModeTransitionShell(host);

            for (var index = 0; index < 50; index++)
            {
                var entered = await shell.EnterAsync(
                    Context("session:" + index), gateway, gateway);
                Assert.IsTrue(entered.Succeeded, "enter " + index + ": " + entered.Message);
                var exited = await shell.ExitAsync();
                Assert.IsTrue(exited.Succeeded, "exit " + index + ": " + exited.Message);
            }

            Assert.AreEqual(CityModeTransitionState.Map, shell.State);
            Assert.IsFalse(CityModePresentationHost.HasActiveInstance);
            Assert.AreEqual(50, host.loadCount);
            Assert.AreEqual(50, host.unloadCount);
            Assert.AreEqual(50, host.restoreCount);
            Assert.AreEqual(50, shell.Metrics.CompletedEntries);
            Assert.AreEqual(50, shell.Metrics.CompletedReturns);
            Assert.Less(shell.Metrics.MaximumEntryMilliseconds, 3000d);
            Assert.Less(shell.Metrics.MaximumReturnMilliseconds, 5000d);
        }

        static CityLaunchContext Context(string sessionId = "session:42")
        {
            return new CityLaunchContext
            {
                sessionId = sessionId,
                cityId = "city:42",
                mapCellId = "cell:42",
                worldSeed = 42,
                worldTick = 100,
                stateRevision = 9,
                timePolicy = CityWorldTimePolicy.PauseWorld,
                worldTimeScalePermille = 0,
                returnViewId = "map:political",
                returnViewStateJson = "{\"x\":12,\"y\":34,\"zoom\":2}"
            };
        }

        sealed class FakeTransitionHost : ICityModeTransitionHost
        {
            readonly TaskCompletionSource<bool> releaseLoad =
                new TaskCompletionSource<bool>();
            public readonly TaskCompletionSource<bool> loadEntered =
                new TaskCompletionSource<bool>();
            public readonly RecordingView view = new RecordingView();
            public bool blockLoad;
            public bool holdLoad;
            public bool failLoad;
            public int loadCount;
            public int unloadCount;
            public int restoreCount;
            public CityLaunchContext restoredContext;

            public async Task<ICityModePresentationView> LoadCityAsync(
                CityLaunchContext context,
                IProgress<float> progress,
                CancellationToken cancellationToken)
            {
                loadCount++;
                loadEntered.TrySetResult(true);
                progress.Report(0.5f);
                if (failLoad)
                    throw new InvalidOperationException("synthetic scene load failure");
                if (blockLoad)
                    await Task.Delay(Timeout.Infinite, cancellationToken);
                if (holdLoad)
                {
                    using (cancellationToken.Register(() => releaseLoad.TrySetCanceled()))
                        await releaseLoad.Task;
                }
                return view;
            }

            public Task UnloadCityAsync(
                CityLaunchContext context,
                CancellationToken cancellationToken)
            {
                unloadCount++;
                return Task.CompletedTask;
            }

            public Task RestoreMapAsync(
                CityLaunchContext context,
                CancellationToken cancellationToken)
            {
                restoreCount++;
                restoredContext = context;
                return Task.CompletedTask;
            }

            public void ReleaseLoad()
            {
                releaseLoad.TrySetResult(true);
            }
        }

        sealed class RecordingObserver : ICityModeTransitionObserver
        {
            public readonly List<CityModeTransitionState> states =
                new List<CityModeTransitionState>();
            public readonly List<float> progress = new List<float>();
            public CityModeErrorCode lastError;

            public void StateChanged(CityModeTransitionState state)
            {
                states.Add(state);
            }

            public void ProgressChanged(float progress01)
            {
                progress.Add(progress01);
            }

            public void Failed(CityModeErrorCode error, string message)
            {
                lastError = error;
            }
        }

        sealed class RecordingView : ICityModePresentationView
        {
            public string openedCityId;
            public long presentedRevision = -1;
            public int closeCount;

            public void Open(CityLaunchContext context)
            {
                openedCityId = context.cityId;
            }

            public void Present(CitySnapshotEnvelope snapshot)
            {
                presentedRevision = snapshot.stateRevision;
            }

            public void CompleteIntent(CityIntentReceipt receipt)
            {
            }

            public void Close()
            {
                closeCount++;
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
                    payloadSha256 = new string('c', 64)
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
