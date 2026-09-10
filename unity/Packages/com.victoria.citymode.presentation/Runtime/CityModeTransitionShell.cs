using System;
using System.Diagnostics;
using System.Threading;
using System.Threading.Tasks;
using Victoria.CityMode.Integration;

namespace Victoria.CityMode.Presentation
{
    public enum CityModeTransitionState
    {
        Map = 0,
        LoadingCity = 1,
        City = 2,
        ReturningToMap = 3,
        Failed = 4,
        Disposed = 5
    }

    /// <summary>
    /// Host-owned scene port. LoadCityAsync resolves the view contained in the
    /// loaded city scene; unload and map restoration must be idempotent so they
    /// can also serve as rollback operations.
    /// </summary>
    public interface ICityModeTransitionHost
    {
        Task<ICityModePresentationView> LoadCityAsync(
            CityLaunchContext context,
            IProgress<float> progress,
            CancellationToken cancellationToken);

        Task UnloadCityAsync(
            CityLaunchContext context,
            CancellationToken cancellationToken);

        Task RestoreMapAsync(
            CityLaunchContext context,
            CancellationToken cancellationToken);
    }

    /// <summary>
    /// Optional UI observer for a loading screen. Observer failures never change
    /// the authoritative transition result.
    /// </summary>
    public interface ICityModeTransitionObserver
    {
        void StateChanged(CityModeTransitionState state);
        void ProgressChanged(float progress01);
        void Failed(CityModeErrorCode error, string message);
    }

    public sealed class CityModeTransitionBudgets
    {
        public static CityModeTransitionBudgets Default { get; } =
            new CityModeTransitionBudgets(
                TimeSpan.FromSeconds(10),
                TimeSpan.FromSeconds(3),
                TimeSpan.FromSeconds(5));

        public CityModeTransitionBudgets(
            TimeSpan coldEntryTimeout,
            TimeSpan warmEntryTimeout,
            TimeSpan returnTimeout)
        {
            if (coldEntryTimeout <= TimeSpan.Zero ||
                warmEntryTimeout <= TimeSpan.Zero ||
                returnTimeout <= TimeSpan.Zero)
                throw new ArgumentOutOfRangeException(nameof(coldEntryTimeout));
            ColdEntryTimeout = coldEntryTimeout;
            WarmEntryTimeout = warmEntryTimeout;
            ReturnTimeout = returnTimeout;
        }

        public TimeSpan ColdEntryTimeout { get; }
        public TimeSpan WarmEntryTimeout { get; }
        public TimeSpan ReturnTimeout { get; }
    }

    public sealed class CityModeTransitionMetrics
    {
        public int CompletedEntries { get; internal set; }
        public int CompletedReturns { get; internal set; }
        public double LastEntryMilliseconds { get; internal set; }
        public double LastReturnMilliseconds { get; internal set; }
        public double ColdEntryMilliseconds { get; internal set; }
        public double MaximumWarmEntryMilliseconds { get; internal set; }
        public double MaximumEntryMilliseconds { get; internal set; }
        public double MaximumReturnMilliseconds { get; internal set; }
        public long PeakManagedMemoryDeltaBytes { get; internal set; }

        internal void RecordEntry(double milliseconds, long memoryDeltaBytes)
        {
            if (CompletedEntries == 0)
                ColdEntryMilliseconds = milliseconds;
            else
                MaximumWarmEntryMilliseconds = Math.Max(
                    MaximumWarmEntryMilliseconds, milliseconds);
            CompletedEntries++;
            LastEntryMilliseconds = milliseconds;
            MaximumEntryMilliseconds = Math.Max(MaximumEntryMilliseconds, milliseconds);
            PeakManagedMemoryDeltaBytes = Math.Max(
                PeakManagedMemoryDeltaBytes,
                Math.Max(0L, memoryDeltaBytes));
        }

        internal void RecordReturn(double milliseconds, long memoryDeltaBytes)
        {
            CompletedReturns++;
            LastReturnMilliseconds = milliseconds;
            MaximumReturnMilliseconds = Math.Max(MaximumReturnMilliseconds, milliseconds);
            PeakManagedMemoryDeltaBytes = Math.Max(
                PeakManagedMemoryDeltaBytes,
                Math.Max(0L, memoryDeltaBytes));
        }
    }

    public sealed class CityModeTransitionResult
    {
        CityModeTransitionResult(
            bool succeeded,
            CityModeErrorCode error,
            string message)
        {
            Succeeded = succeeded;
            Error = error;
            Message = message ?? string.Empty;
        }

        public bool Succeeded { get; }
        public CityModeErrorCode Error { get; }
        public string Message { get; }

        internal static CityModeTransitionResult Success()
        {
            return new CityModeTransitionResult(true, CityModeErrorCode.None, string.Empty);
        }

        internal static CityModeTransitionResult Failure(
            CityModeErrorCode error,
            string message)
        {
            return new CityModeTransitionResult(false, error, message);
        }
    }

    /// <summary>
    /// Reversible map-to-city state machine. It owns orchestration only: the host
    /// still owns scene loading, map viewport/selection restoration, world time,
    /// the authoritative gateway and persistence.
    /// </summary>
    public sealed class CityModeTransitionShell : IDisposable
    {
        readonly object gate = new object();
        readonly ICityModeTransitionHost host;
        readonly ICityModeTransitionObserver observer;
        readonly CityModeTransitionBudgets budgets;
        readonly CancellationTokenSource lifetime = new CancellationTokenSource();

        CityModeTransitionState state = CityModeTransitionState.Map;
        CityModeSession session;
        CityModePresentationHost presentation;
        CityLaunchContext context;
        bool operationInFlight;
        bool disposed;

        public CityModeTransitionShell(
            ICityModeTransitionHost host,
            ICityModeTransitionObserver observer = null,
            CityModeTransitionBudgets budgets = null)
        {
            this.host = host ?? throw new ArgumentNullException(nameof(host));
            this.observer = observer;
            this.budgets = budgets ?? CityModeTransitionBudgets.Default;
            Metrics = new CityModeTransitionMetrics();
        }

        public CityModeTransitionState State
        {
            get
            {
                lock (gate)
                    return state;
            }
        }

        public CityLaunchContext CurrentContext
        {
            get
            {
                lock (gate)
                    return context;
            }
        }

        public CityModeTransitionMetrics Metrics { get; }
        public bool IsOperationInFlight
        {
            get
            {
                lock (gate)
                    return operationInFlight;
            }
        }

        public Task<CityModeTransitionResult> EnterAsync(
            CityLaunchContext launchContext,
            ICityModeSnapshotSource snapshotSource,
            ICityModeIntentSink intentSink,
            CancellationToken cancellationToken = default)
        {
            CityModeErrorCode error;
            if (!CityModeContractValidation.TryValidate(launchContext, out error))
                return Task.FromResult(CityModeTransitionResult.Failure(
                    error, "City launch context is invalid."));
            if (snapshotSource == null || intentSink == null)
                return Task.FromResult(CityModeTransitionResult.Failure(
                    CityModeErrorCode.HostUnavailable,
                    "The authoritative gateway is unavailable."));

            lock (gate)
            {
                if (disposed)
                    return Task.FromResult(CityModeTransitionResult.Failure(
                        CityModeErrorCode.HostUnavailable, "Transition shell is disposed."));
                if (operationInFlight || state != CityModeTransitionState.Map)
                    return Task.FromResult(CityModeTransitionResult.Failure(
                        CityModeErrorCode.SessionAlreadyActive,
                        "A city transition or session is already active."));
                operationInFlight = true;
                state = CityModeTransitionState.LoadingCity;
            }

            SafeStateChanged(CityModeTransitionState.LoadingCity);
            return EnterCoreAsync(
                launchContext, snapshotSource, intentSink, cancellationToken);
        }

        public Task<CityModeTransitionResult> ExitAsync(
            CancellationToken cancellationToken = default)
        {
            CityLaunchContext activeContext;
            lock (gate)
            {
                if (disposed)
                    return Task.FromResult(CityModeTransitionResult.Failure(
                        CityModeErrorCode.HostUnavailable, "Transition shell is disposed."));
                if (operationInFlight)
                    return Task.FromResult(CityModeTransitionResult.Failure(
                        CityModeErrorCode.SessionAlreadyActive,
                        "Another transition is still active."));
                if (state != CityModeTransitionState.City || context == null)
                    return Task.FromResult(CityModeTransitionResult.Failure(
                        CityModeErrorCode.HostUnavailable, "No city session is active."));
                operationInFlight = true;
                state = CityModeTransitionState.ReturningToMap;
                activeContext = context;
            }

            SafeStateChanged(CityModeTransitionState.ReturningToMap);
            return ExitCoreAsync(activeContext, cancellationToken);
        }

        async Task<CityModeTransitionResult> EnterCoreAsync(
            CityLaunchContext launchContext,
            ICityModeSnapshotSource snapshotSource,
            ICityModeIntentSink intentSink,
            CancellationToken cancellationToken)
        {
            var stopwatch = Stopwatch.StartNew();
            var memoryBefore = GC.GetTotalMemory(false);
            var loadRequested = false;
            var timeout = Metrics.CompletedEntries == 0
                ? budgets.ColdEntryTimeout
                : budgets.WarmEntryTimeout;

            try
            {
                using (var operation = CancellationTokenSource.CreateLinkedTokenSource(
                           cancellationToken, lifetime.Token))
                {
                    loadRequested = true;
                    var view = await RunGuardedAsync(
                        token => host.LoadCityAsync(
                            launchContext, new ProgressRelay(SafeProgressChanged), token),
                        timeout,
                        operation.Token);
                    if (view == null)
                        throw new TransitionFailureException(
                            CityModeErrorCode.InvalidPayload,
                            "The loaded city scene did not expose a presentation view.");

                    CityModeErrorCode error;
                    CityModeSession openedSession;
                    if (!CityModeSession.TryOpen(
                            launchContext,
                            snapshotSource,
                            intentSink,
                            out openedSession,
                            out error))
                        throw new TransitionFailureException(
                            error, "The authoritative city session could not be opened.");
                    session = openedSession;

                    CityModePresentationHost createdPresentation;
                    if (!CityModePresentationHost.TryCreate(
                            session, out createdPresentation, out error))
                        throw new TransitionFailureException(
                            error, "The city presentation could not be created.");
                    presentation = createdPresentation;
                    if (!presentation.TryAttachView(view, out error))
                        throw new TransitionFailureException(
                            error, "The loaded city view could not be attached.");
                }

                stopwatch.Stop();
                lock (gate)
                {
                    context = launchContext;
                    state = CityModeTransitionState.City;
                }
                Metrics.RecordEntry(
                    stopwatch.Elapsed.TotalMilliseconds,
                    GC.GetTotalMemory(false) - memoryBefore);
                SafeProgressChanged(1f);
                SafeStateChanged(CityModeTransitionState.City);
                return CityModeTransitionResult.Success();
            }
            catch (TransitionTimeoutException)
            {
                return await FailEntryAsync(
                    launchContext,
                    loadRequested,
                    CityModeErrorCode.Timeout,
                    "City loading exceeded its budget.");
            }
            catch (OperationCanceledException)
            {
                return await FailEntryAsync(
                    launchContext,
                    loadRequested,
                    CityModeErrorCode.Cancelled,
                    "City loading was cancelled.");
            }
            catch (TransitionFailureException failure)
            {
                return await FailEntryAsync(
                    launchContext, loadRequested, failure.Error, failure.Message);
            }
            catch (Exception exception)
            {
                return await FailEntryAsync(
                    launchContext,
                    loadRequested,
                    CityModeErrorCode.InternalError,
                    "City loading failed: " + exception.Message);
            }
            finally
            {
                lock (gate)
                    operationInFlight = false;
            }
        }

        async Task<CityModeTransitionResult> ExitCoreAsync(
            CityLaunchContext activeContext,
            CancellationToken cancellationToken)
        {
            var stopwatch = Stopwatch.StartNew();
            var memoryBefore = GC.GetTotalMemory(false);
            var error = CityModeErrorCode.None;
            var message = string.Empty;

            ReleasePresentationAndSession();
            try
            {
                await RunGuardedAsync(
                    token => host.UnloadCityAsync(activeContext, token),
                    budgets.ReturnTimeout,
                    cancellationToken);
            }
            catch (TransitionTimeoutException)
            {
                error = CityModeErrorCode.Timeout;
                message = "City unload exceeded its budget.";
            }
            catch (OperationCanceledException)
            {
                error = CityModeErrorCode.Cancelled;
                message = "City unload was cancelled.";
            }
            catch (Exception exception)
            {
                error = CityModeErrorCode.InternalError;
                message = "City unload failed: " + exception.Message;
            }

            try
            {
                await RunGuardedAsync(
                    token => host.RestoreMapAsync(activeContext, token),
                    budgets.ReturnTimeout,
                    CancellationToken.None);
            }
            catch (Exception exception)
            {
                if (error == CityModeErrorCode.None)
                {
                    error = exception is TransitionTimeoutException
                        ? CityModeErrorCode.Timeout
                        : CityModeErrorCode.InternalError;
                    message = "Map restoration failed: " + exception.Message;
                }
            }

            stopwatch.Stop();
            lock (gate)
            {
                context = null;
                state = disposed
                    ? CityModeTransitionState.Disposed
                    : CityModeTransitionState.Map;
                operationInFlight = false;
            }
            Metrics.RecordReturn(
                stopwatch.Elapsed.TotalMilliseconds,
                GC.GetTotalMemory(false) - memoryBefore);
            SafeStateChanged(State);
            if (error == CityModeErrorCode.None)
                return CityModeTransitionResult.Success();
            SafeFailed(error, message);
            return CityModeTransitionResult.Failure(error, message);
        }

        async Task<CityModeTransitionResult> FailEntryAsync(
            CityLaunchContext failedContext,
            bool loadRequested,
            CityModeErrorCode error,
            string message)
        {
            lock (gate)
                state = CityModeTransitionState.Failed;
            SafeStateChanged(CityModeTransitionState.Failed);
            SafeFailed(error, message);
            ReleasePresentationAndSession();

            lock (gate)
                state = CityModeTransitionState.ReturningToMap;
            SafeStateChanged(CityModeTransitionState.ReturningToMap);
            if (loadRequested)
            {
                try
                {
                    await RunGuardedAsync(
                        token => host.UnloadCityAsync(failedContext, token),
                        budgets.ReturnTimeout,
                        CancellationToken.None);
                }
                catch
                {
                    // Restoration is still attempted even when unload rollback fails.
                }
            }
            try
            {
                await RunGuardedAsync(
                    token => host.RestoreMapAsync(failedContext, token),
                    budgets.ReturnTimeout,
                    CancellationToken.None);
            }
            catch
            {
                // The primary, versioned transition error remains the result.
            }

            lock (gate)
            {
                context = null;
                state = disposed
                    ? CityModeTransitionState.Disposed
                    : CityModeTransitionState.Map;
            }
            SafeStateChanged(State);
            return CityModeTransitionResult.Failure(error, message);
        }

        static async Task<T> RunGuardedAsync<T>(
            Func<CancellationToken, Task<T>> operationFactory,
            TimeSpan timeout,
            CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            using (var linked = CancellationTokenSource.CreateLinkedTokenSource(
                       cancellationToken))
            {
                var operation = operationFactory(linked.Token);
                if (operation == null)
                    throw new InvalidOperationException("Transition host returned no task.");
                var guard = Task.Delay(timeout, cancellationToken);
                var completed = await Task.WhenAny(operation, guard);
                if (completed == operation)
                    return await operation;
                linked.Cancel();
                ObserveFault(operation);
                cancellationToken.ThrowIfCancellationRequested();
                throw new TransitionTimeoutException();
            }
        }

        static async Task RunGuardedAsync(
            Func<CancellationToken, Task> operationFactory,
            TimeSpan timeout,
            CancellationToken cancellationToken)
        {
            await RunGuardedAsync(
                async token =>
                {
                    await operationFactory(token);
                    return true;
                },
                timeout,
                cancellationToken);
        }

        static void ObserveFault(Task task)
        {
            task.ContinueWith(
                completed =>
                {
                    var ignored = completed.Exception;
                },
                CancellationToken.None,
                TaskContinuationOptions.OnlyOnFaulted |
                TaskContinuationOptions.ExecuteSynchronously,
                TaskScheduler.Default);
        }

        void ReleasePresentationAndSession()
        {
            presentation?.Dispose();
            presentation = null;
            session?.Dispose();
            session = null;
        }

        void SafeStateChanged(CityModeTransitionState next)
        {
            try
            {
                observer?.StateChanged(next);
            }
            catch
            {
                // Loading UI is observational only.
            }
        }

        void SafeProgressChanged(float progress)
        {
            try
            {
                observer?.ProgressChanged(Math.Max(0f, Math.Min(1f, progress)));
            }
            catch
            {
                // Loading UI is observational only.
            }
        }

        void SafeFailed(CityModeErrorCode error, string message)
        {
            try
            {
                observer?.Failed(error, message);
            }
            catch
            {
                // Loading UI is observational only.
            }
        }

        public void Dispose()
        {
            lock (gate)
            {
                if (disposed)
                    return;
                disposed = true;
                state = CityModeTransitionState.Disposed;
            }
            lifetime.Cancel();
            ReleasePresentationAndSession();
            lifetime.Dispose();
            SafeStateChanged(CityModeTransitionState.Disposed);
        }

        sealed class ProgressRelay : IProgress<float>
        {
            readonly Action<float> callback;

            public ProgressRelay(Action<float> callback)
            {
                this.callback = callback;
            }

            public void Report(float value)
            {
                callback(value);
            }
        }

        sealed class TransitionFailureException : Exception
        {
            public TransitionFailureException(CityModeErrorCode error, string message)
                : base(message)
            {
                Error = error;
            }

            public CityModeErrorCode Error { get; }
        }

        sealed class TransitionTimeoutException : TimeoutException
        {
        }
    }
}
