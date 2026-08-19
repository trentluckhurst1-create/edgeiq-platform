    // ADHOC 20201008 P.I. i) Integrated AWT Reports
    //                    ii) Refactored method ...common.ShowAll() to ...ShowAllSections(displayMode)
    //                   iii) Refactored method ResizeRepeater() to process individual Wind Repeaters
    //                    iv) Refactored method HelperRefreshElement for individual Wind Repeaters
    // ADHOC 20210613 P.I. Added ability to dectec the "reload" initiator
    // ADHOC 20220101 P.I. Merged these two Cases - only difference is the Status Message
    // @todo Do Event Listeners need to be cleared if we resize the window? {@see https://thedailywtf.com/articles/quite-the-event }
    window.its = window.its || {};
    window.its.visualiser = window.its.visualiser || {};
    
    window.its.visualiser.common.Init();                                        // Invoke / initialise  Common JS
    window.addEventListener('beforeunload', function() {
        window.its.visualiser.base.auditTool.Destroy();
        window.its.visualiser.base.apiTool.Destroy();
    });

    window.its.visualiser.base = {
        wdvCommon: window.its.visualiser.common,
        descartes: 'WDV Base Object',
        
        PostUpdate: function(updateContent) {
            var that = window.its.visualiser.base;
            var disabledMetrics = null;
            var metrics = null;
            var useId = null;
            var advisory = null;
            window.its.visualiser.base.WindDirectionImage(updateContent['winddirection-current']);
            if (updateContent.hasOwnProperty('disableMetric')) {
                disabledMetrics = updateContent.disableMetric;
                metrics = disabledMetrics.length;
                for (i=0; i<metrics; i++) {
                    useId = disabledMetrics[i] + "-metric";
                    advisory = _ucFirst(disabledMetrics[i]) + " Metric has been Disabled in Configuration";
                    document.getElementById(useId).style.display = "none";
                    window.its.visualiser.common.ShowAdvisory(advisory, disabledMetrics[i]);
                }
            }
            return true;
        },
        WarningTool: {
            descartes: 'Warning Tool',
            displayIcon: document.getElementById('warning-tool'),
            advisory: {
                "reportStatus": null
            },
            
            Display: function() {
                window.its.visualiser.common.LocalLog('Executing: Warning Tool Display', descartes, 'debug');
                var that = window.its.visualiser.base.WarningTool;
                var advisoryElement = document.getElementById('advisory-notice');
                if (advisoryElement.parentNode.style.display === 'none') {
                    window.its.visualiser.base.CheckUpdateStatus(that.advisory);
                }
                else {
                    advisoryElement.innerHTML = '<dd>,</dd>';
                    advisoryElement.parentNode.style.display = 'none';
                }
            },
            Init: function() {
                window.its.visualiser.common.LocalLog('Executing: Warning Tool Init', descartes, 'debug');
                var that = window.its.visualiser.base.WarningTool;
                var methodReturn = false;
                var advisoryCount = 0;
                if (that.displayIcon) {
                    that.displayIcon.style.display = 'none';
                    if (window.lastUpdateContent.hasOwnProperty('reportStatus')) {
                        that.advisory.reportStatus = window.lastUpdateContent.reportStatus;
                        for (var section in that.advisory.reportStatus) {
                            advisoryCount = advisoryCount + that.advisory.reportStatus[section].length;
                        }
                    }
                    if (advisoryCount > 0) {
                        that.displayIcon.style.display = 'block';
                        methodreturn = true;
                    }
                }
                return methodReturn;
            }
        },
        auditTool: {
            descartes: 'Audit Tool',
            available: window.runtimeAuditTrace,
            auditWindow: null,
            controlParent: document.getElementById('trace-tool'),
            controlObject: null,
            windowName: 'wdv-audit-trace-' + window.clientName,
            windowTemplate: '<!doctype html>\n\
<html lang="en">\n\
    <head>\n\
        <meta charset="utf-8">\n\
        <title>(' + window.its.visualiser.common.codeBase.toUpperCase() + ') WDV Audit Trace For ' + window.clientName + '</title>\n\
        <script>\n\
            window.addEventListener("beforeunload", function() { window.opener.its.visualiser.base.auditTool.Destroy(); });\n\
        </script>\n\
    </head>\n\
    <body style="width:100%;height:900px;font-family:verdanna;">\n\
        <div style="width:1000px;margin:0 auto;">\n\
            <div style="width:100%;height:100px;">\n\
                <h3>' + window.its.visualiser.common.codeBase.toUpperCase() + ' Run Trace (' + window.clientName + ')</h3>\n\
                <button style="cursor:pointer;" onclick="window.close();">Close</button>\n\
                <button style="cursor:pointer;" onclick="window.opener.location.reload();">Reload Parent</button>\n\
                <button style="cursor:pointer;" data-is-button="trace-tool" onclick="window.opener.ButtonAction(\'update-1\', this);">Update Parent</button>\n\
            </div>\n\
            <div style="width:100%;height:800px;overflow:auto;font-family:mono-space;">\n\
                <pre id="audit-trace" style="line-height:13px;"></pre>\n\
            </div>\n\
        </div>\n\
    </body>\n\
</html>',
            toolContent: '',
            Display: function() {
                window.its.visualiser.common.LocalLog('Executing: Audit Tool Display', descartes, 'debug');
                var that = window.its.visualiser.base.auditTool;
                var methodReturn = false;
                if (that.available === 'active') {
                    that.controlObject = that.controlParent.firstElementChild;
                    if (that.auditWindow === null) {
                        that.auditWindow = that._create(that.windowName, window.clientName);
                        that.Refresh();
                    }
                    else {
                        window._blinkIcon(that.controlObject);
                        window._blinkIcon(that.controlObject, true);
                        that.auditWindow.focus();
                    }
                    methodReturn = true;
                }
                return methodReturn;
            },
            Refresh: function () {
                window.its.visualiser.common.LocalLog('Executing: Audit Tool Refresh', descartes, 'debug');
                var that = window.its.visualiser.base.auditTool;
                var methodReturn = false;
                var content = window.uiAuditTrace + that.toolContent;
                content = content.replace('<', '&lt;');
                content = content.replace('>', '&gt;');
                if (that.auditWindow) {
                    window._blinkIcon(that.controlObject, true);
                    that.auditWindow.document.getElementById('audit-trace').innerHTML = content;
                    that.auditWindow.focus();
                    methodReturn = true;
                }
                return methodReturn;
            },
            Destroy: function() {
                window.its.visualiser.common.LocalLog('Executing: Audit Tool Destroy', descartes, 'debug');
                var that = window.its.visualiser.base.auditTool;
                window._blinkIcon(that.controlObject);
                if (that.auditWindow) {
                    that.auditWindow.close();
                    that.auditWindow = null;
                }
            },
            _create: function (resourceName, clientName) {
                var that = window.its.visualiser.base.auditTool;
                var temp = window.open('', resourceName, "menubar=no,location=no,resizable=yes,scrollbars=yes,status=no");
                temp.document.write(that.windowTemplate);
                return temp;
            }
        },
        apiTool: {
            descartes: 'API Response Tool',
            available: window.runtimeAuditTrace,
            auditWindow: null,
            controlParent: document.getElementById('api-tool'),
            controlObject: null,
            windowName: 'wdv-api-response-' + window.clientName,
            windowTemplate: '<!doctype html>\n\
<html lang="en">\n\
    <head>\n\
        <meta charset="utf-8">\n\
        <title>(' + window.its.visualiser.common.codeBase.toUpperCase() + ') WDV API Response For ' + window.clientName + '</title>\n\
        <script>\n\
            window.addEventListener("beforeunload", function() { window.opener.its.visualiser.base.apiTool.Destroy(); });\n\
        </script>\n\
    </head>\n\
    <body style="width:100%;height:900px;font-family:verdanna;">\n\
        <div style="width:1000px;margin:0 auto;">\n\
            <div style="width:100%;height:100px;">\n\
                <h3>' + window.its.visualiser.common.codeBase.toUpperCase() + ' API Response (' + window.clientName + ')</h3>\n\
                <button style="cursor:pointer;" onclick="window.close();">Close</button>\n\
                <button style="cursor:pointer;" onclick="window.opener.location.reload();">Reload Parent</button>\n\
                <button style="cursor:pointer;" data-is-button="api-tool" onclick="window.opener.ButtonAction(\'update-1\', this);">Update Parent</button>\n\
            </div>\n\
            <div style="width:100%;height:800px;overflow:auto;font-family:mono-space;">\n\
                <pre id="api-response" style="line-height:13px;"></pre>\n\
            </div>\n\
        </div>\n\
    </body>\n\
</html>',
            toolContent: '',
            Display: function() {
                window.its.visualiser.common.LocalLog('Executing: API Tool Display', descartes, 'debug');
                var that = window.its.visualiser.base.apiTool;
                var methodReturn = false;
                if (that.available === 'active') {
                    that.controlObject = that.controlParent.firstElementChild;
                    if (that.auditWindow === null) {
                        that.auditWindow = that._create(that.windowName, window.clientName);
                        that.Refresh();
                    }
                    else {
                        window._blinkIcon(that.controlObject);
                        window._blinkIcon(that.controlObject, true);
                        that.auditWindow.focus();
                    }
                }
                return methodReturn;
            },
            Refresh: function () {
                window.its.visualiser.common.LocalLog('Executing: API Tool Refresh', descartes, 'debug');
                var that = window.its.visualiser.base.apiTool;
                var methodReturn = false;
                var content = that.toolContent;
                content = content.replace('<', '&lt;');
                content = content.replace('>', '&gt;');
                if (that.auditWindow) {
                    window._blinkIcon(that.controlObject, true);
                    that.auditWindow.document.getElementById('api-response').innerHTML = content;
                    that.auditWindow.focus();
                    methodReturn = true;
                }
                return methodReturn;
            },
            Destroy: function() {
                window.its.visualiser.common.LocalLog('Executing: API Tool Destroy', descartes, 'debug');
                var that = window.its.visualiser.base.apiTool;
                window._blinkIcon(that.controlObject);
                if (that.auditWindow) {
                    that.auditWindow.close();
                    that.auditWindow = null;
                }
            },
            _create: function (resourceName, clientName) {
                var that = window.its.visualiser.base.apiTool;
                var temp = window.open('', resourceName, "menubar=no,location=no,resizable=yes,scrollbars=yes,status=no");
                temp.document.write(that.windowTemplate);
                return temp;
            }
        },
        
        WindDirectionImage: function(windDirection) {
            this.wdvCommon.LocalLog('Executing: WindDirectionImage', this.descartes, 'debug');
            var imgList = ['going-wind-dir-repeat', 'awt-wind-dir-repeat','wind-dir-icon'];
            var bgList = ['winddirection-current-rose'];
            var useAdjective = null;
            var thisImage = null;
            var newImage = null;
            var activeImage = '/';
            var inactiveImage = '/blank-';
            if (windDirection === '#') {
                useAdjective = inactiveImage;
            }
            else {
                useAdjective = activeImage;
            }
            for (var i = 0; i < imgList.length; i++) {
                thisImage = document.getElementById(imgList[i]);
                if (thisImage) {
                    newImage = thisImage.src.replace(inactiveImage, activeImage);
                    switch (useAdjective) {
                        case '/blank-':
                            newImage = newImage.replace('images/', 'images' + useAdjective);
                            break;
                        default:
                    }
                    thisImage.src = newImage;
                }
            }
            for (var i = 0; i < bgList.length; i++) {
                thisImage = document.getElementById(bgList[i]);
                if (thisImage) {
                    newImage = window.getComputedStyle(thisImage).getPropertyValue('background-image');
                    newImage = newImage.replace(inactiveImage, activeImage);
                    switch (useAdjective) {
                        case '/blank-':
                            newImage = newImage.replace('images/', 'images' + useAdjective);
                            break;
                        default:
                    }
                    thisImage.style.backgroundImage = newImage;
                }
            }
            return true;
        },
        
        CheckUpdateStatus: function (newContent) {
            this.wdvCommon.LocalLog('Executing: CheckUpdateStatus', this.descartes, 'debug');
            var advisoryMessage = '';
            var noticeList = null;
            if (newContent.hasOwnProperty('reportStatus')) {
                for (var section in newContent['reportStatus']) {
                    noticeList = newContent['reportStatus'][section];
                    if (noticeList.length > 0) {
                        advisoryMessage+= '<dt>' + this.wdvCommon.UCFirst(section) + ':</dt>';
                        advisoryMessage+= '<dd>' + noticeList.join('</dd><dd>') + '</dd>';
                    }
                }
                if (advisoryMessage.length > 0) {
                    window.its.visualiser.common.ShowAdvisory(advisoryMessage);
                }
            }
        return true;
        },
        
        carousel: {
            descartes: 'Sensor Group Carousel',
            sensorGroups: ["temperature"],
            
            SetDefault: function (groupObject, groupName) {
                window.its.visualiser.common.LocalLog('Executing: Init', descartes, 'debug');
                var that = window.its.visualiser.base.carousel;
                var methodReturn = false;
                var titleObject = null;
                var targetTitle = null;
                var titleModifier = '';
                var metricObject = document.getElementById(groupName + '-metric');
                if (typeof(metricObject) === 'object') {
                    titleObject = metricObject.querySelector('.metric-title');
                        if (typeof( targetTitle) !== 'undefined') {
                        if (groupObject.hasOwnProperty('default')) {
                            targetTitle = titleObject.innerHTML;
                            titleModifier = window.its.visualiser.common.UCFirst(groupObject["default"]) + "&nbsp;";
                            if (targetTitle.indexOf(titleModifier) < 0) { titleObject.innerHTML = titleModifier + targetTitle;}
                            methodReturn = true;
                        }
                    }
                }
                return methodReturn;
            },
            
            Init: function (carouselObject) {
                window.its.visualiser.common.LocalLog('Executing: Init', descartes, 'debug');
                var that = window.its.visualiser.base.carousel;
                var methodReturn = false;
                window.sensorCarousel = carouselObject;
                for ( var group in that.sensorGroups) {
                    if (window.sensorCarousel.hasOwnProperty(group)) {
                        that.SetDefault(window.sensorCarousel[group], group);
                        methodReturn = true;
                    }
                };
                return methodReturn;
            }
            
        }
    };
    
    var descartes = 'WDV Base';
    var streamApiXhttp = null;
    var useProtocol = null;
    var queryString = location.search;
    var streamHost = null;
    var viewCountdown = document.getElementsByClassName('view-countdown')[0];
    var updateCountdown = document.getElementById('update-countdown');
    var updateTimer = null;                                                     // Holder for WDV Update Timeout Event
    var viewStatus = document.getElementsByClassName('refresh-status')[0];
    var updateStatus = document.getElementById('update-status');
    var retryUpdate = 10;                                                       // Seconds between Stream API Attempts
    var retryCount = 0;                                                         // Maximum Stream API Attempts to make
    var haveRetried = 0;                                                        // Counter for (current) Stream API Attempts
    var lastUpdateContent = null;
    var statusPriority = new Array('none', 'info', 'notice', 'warning', 'error', 'fatal');
    var reportPriority = 0;
    var responseTimer = null;                                                   // Holder for AJAX Timeout Event
    var cmsPopupInterval = 30000;                                               // Milliseconds that the Mini-CMS will display
    var cmsPopupTimer = null;                                                   // Holder for Mini-CMS Timeout Event
    var errorInterval = 5000;                                                   // Milliseconds that a JS Error message will be displayed
    var moistureTakenAt = null;
    var manualRain = null;
    var compressable = new Array(
            'additional-comment',
            'going-report',
            'rail-report',
            'stick-report',
            'weather-comment',
            'irrigation-report',
            'stalls-report',
            'awt-going-report',
            'awt-stalls-report',
            'awt-additional-comment'
        );
    var compressText = {
            "primary": {
                "fontSize": "1.2rem",
                "lineHeight": "1.4rem"
            },
            "secondary": {
                "fontSize": "1rem",
                "lineHeight": "1.4rem"
            },
            "tertiary": {
                "fontSize": "1rem",
                "lineHeight": "1.2rem"
            },
            "quaternary": {
                "fontSize": ".8rem",
                "lineHeight": "1.2rem"
            }
        };
    var skipText = 'skip this';
    var noDataText = '<span class="no-data-error">N/a</span>';
    /**
     * Set a Listener to intercept errors generated by the WDV Web UI
     * 
     *  - If there is a Browser Console, errors will be logged there.
     *  On the successful loading of the WDV Common JS, it will:
     *  - Initialise the WDV Common JS
     *  - Log errors using the Method its.visualiser.common.ReportError()
     *  - Use the HTTP Protocol, Host Server and sub-domain (as determined by
     *    the WDV Common JS) to set Property streamHost
     *  - Call Method StreamInit() with "success"
     *  Otherwise, it will call Method StreamInit() with "failure"
     *  
     * @note the following are the standard JavaScript Error Properties
     * @param {string} msg
     * @param {type} url
     * @param {type} lineNo
     * @param {type} columnNo
     * @param {type} error
     * @returns {Boolean}
     */
    try {
        useProtocol = window.its.visualiser.common.useProtocol;
        streamHost = window.its.visualiser.common.useHost;
        if (window.self !== window.top) { window.licenseDelay = setTimeout(StreamInit, 1000, false); }    // Give License time to communicate
        else { StreamInit(false); }
    }
    catch (error) {
        StreamInit(true);
    }
    /**
     * Will Initialise the WDV Web UI
     * 
     * if there is no "error":
     * - Propagate the Query String Parameter test to the WDV Stream API Call
     * - Set a Listener to respond to the window being resized
     * - Initiate the first call to the WDV Stream API
     * Else:
     * - "Blank" the Going and Weather Displays
     * - Display a generic error message
     * 
     * @note An Error is is determined if either the WDV Common JS could not be<br>
     * is not loaded (syntax / DOM errors) or fails to initialise
     * @see its.visualiser.common.Init()
     * 
     * @param {boolean} errorCondition FALSE if the WDV Common JS could be loaded and initialised
     * @returns {Boolean} TRUE or FALSE on successful execution as determined by parameter errorCondition. NULL if it didn't.
     */
    function StreamInit(errorCondition) {
        window.its.visualiser.common.LocalLog('Executing: StreamInit', window.descartes, 'debug');
        var methodReturn = false;
        var initialUrl = window._buildUrl('api');
        clearTimeout(window.licenseDelay);
        window.document.body.style.cursor = 'default';
        window.updateInterval = parseInt(window.updateInterval);
        if (errorCondition === false) {
            window.viewStatus.style.visibility = 'visible';
            window.addEventListener('resize', ResizeElements);
            GetVisualiserUpdate(initialUrl);
            methodReturn = true;
        }
        else {
            if (document.getElementById('weather-report-wdv')) {
                document.getElementById('weather-report-wdv').style.display = 'none';
            }
            if (document.getElementById('going-report-wdv')) {
                document.getElementById('going-report-wdv').style.display = 'none';
            }
            if (document.getElementById('awt-report-wdv')) {
                document.getElementById('awt-report-wdv').style.display = 'none';
            }
            document.getElementById('update-status').innerHTML = 'Error: Unable to Load Common JS';
            document.getElementById('update-status').style.visibility = 'visible';
        }
        return methodReturn;
    }
    /**
     * Will create a Timeout Event to initiate an WDV Update Request
     * 
     * The Timeout Event is "stored" in <i><b>property</b> window.updateTimer</i>
     * and <b>will replace</b> any previous Timeout Event. The time (in seconds) until
     * the next refresh is displayed as a "countdown".<br>
     * It uses <i><b>property</b> window.updateInterval</i> for the timeout period.
     * If this is absent, negative or less than <i>minimum</i>, the HMTL Meta Refresh
     * Interval will be used. The Browser's Local Time for the next update will
     * be displayed. If there is no meta refresh there will be no automatic WDV
     * Update Request. A message indicating that a WDV Update requires a reload
     * 
     * @note The minimum is, nominally, twice that of <i><b>property<b> window.responseInterval</i><br>
     *       (as seconds). Setting <i><b>property</b> window.updateTimer</i> to a negative value
     *       will force the use of the <i>meta refresh</i>
     * @param {integer} newInterval
     * @returns {Boolean} <b>TRUE</b> If <i>useInterval</i> is used<br>
     *                    <b>FALSE</b> If <i>meta refresh</i> is used<br>
     *                    <b>NULL</b> If a Reload is required
     */
    function StartUpdateCountdown(newInterval) {
        window.its.visualiser.common.LocalLog('Executing: StartUpdateCountdown', window.descartes, 'debug');
        var methodReturn = null;
        var useInterval = window.updateInterval;
        var minDelay = ((window.responseInterval / 1000) * 3) || 10;
        var newLocation = window._buildUrl('api');
        clearTimeout(window.updateTimer);                                       // ensure previous / current time out is stopped
        if (typeof(newInterval) !== 'undefined') {
            useInterval = parseInt(newInterval);
        }
        if ((useInterval >= 0) && (useInterval < minDelay)) {
            useInterval = minDelay;
        }
        if (useInterval >= minDelay) {
            window.updateCountdown.innerHTML = useInterval;
            window.updateTimer = setInterval(function () {
                var intervalNow = window.updateCountdown.innerHTML;
                intervalNow--;
                if (intervalNow <= 0) {
                    GetVisualiserUpdate(newLocation);
                    intervalNow = window.updateInterval;
                }
                window.updateCountdown.innerHTML = intervalNow;
            }, 1000, newLocation);
            methodReturn = true;
        }
        else {
            var httpEquivList = document.getElementsByTagName('META');
            var checkThis = null;
            var metaReload = -1;
            for (var i = 0; i < httpEquivList.length; i++) {
                checkThis = httpEquivList[i];
                if ((checkThis.hasAttribute('http-equiv')) && (checkThis.getAttribute('http-equiv').toLowerCase() === 'refresh')) {
                    if (checkThis.hasAttribute('content')) {
                        metaReload = parseInt(checkThis.getAttribute('content'));
                    }
                    break;
                }
            }
            if (window.updateCountdown.parentNode) {
                if (metaReload < 0) {
                    window.updateCountdown.parentNode.innerHTML = 'Reload Page to Refresh';
                }
                else {
                    var clientTime = new Date();
                    clientTime.setSeconds(clientTime.getSeconds() + metaReload);
                    window.updateCountdown.parentNode.innerHTML = 'Page will Refresh at ' + clientTime;
                }
            }
        }
    }
    /**
     * Will make an AJAX (XML HTTP Request) Call to the WDV Stream API using GET
     * 
     * @note It expects a valid JSON Response with, at least a "status" and
     *       "content". Any Status other than 0 is a failure. The Content should
     *       have the reason "why"
     * @see TTITS Documentation about Status Codes
     * 
     * Does lots of stuff that's "under the hood" But:
     * - It will check the supplied URL is valid and abort otherwise
     * - It will set a time-out (using Property responseInterval) that will abort
     *   the request because not all Browsers support XMLHttpRequest.timeout()
     * - The time-out will be stored in Property responseTimer and cleared on a
     *   successful connection. Otherwise a "Server Timeout" message will be
     *   displayed
     * - It will do its best to "make sense" of the API Response and display an
     *   appropriate message if it can't
     * On a HTTP 200 Response, it will Call (the Call Sequence is CRITICAL):
     * - UpdateWDV(responsePayload) to "write" the refreshed data;
     * - its.visualiser.common.ShowAllSections() to ensure all display panels are visible
     * - ResizeElements() to dynamically "adjust stuff to fit"
     * 
     * @param {string} updateUrl The URL from which to get the Update
     * @returns {Boolean} Will <b>TRUE</b> if the Request is sent, otherwise <b>FALSE</b>
     */
    function GetVisualiserUpdate(updateUrl) {
        window.its.visualiser.common.LocalLog('Executing: GetVisualiserUpdate', window.descartes, 'debug');
//        ADHOC 20210822 P.I. Not supported by I.E. Do we actually need this?
//                            All we are doing is checking that, if we have something,
//                            that it is a "vaild" URL becaused we failed to create the
//                            new window. And then done nothing about it (disabled the try/catch)
//                            It's going to fail horribly if the is no URL anyway - something we\n\
//                            dont't check for!
//        if (typeof(window.URL) !== 'undefined') {
//        //try {
//                new window.URL(updateUrl);
//        //    }
//        //catch (e) {
//        //window.its.visualiser.common.LocalLog(' now Here', window.descartes, 'debug');
//        //    HelperSetStatus('The supplied Update URL appears to be invalid', 'fatal');
//        //    return false;
//        //}
//        }
        document.body.style.cursor = 'progress';
        streamApiXhttp = new XMLHttpRequest();
        window.responseTimer = setTimeout(
            function() {
                streamApiXhttp.abort();
                document.body.style.cursor = 'default';
            },
            window.responseInterval
        );
        streamApiXhttp.onreadystatechange = function () {
            var methodReturn = false,
                responseData = null,
                responseCode = null,
                responsePayload = null,
                process = false,
                goingContent = document.getElementById('going-report-wdv'),
                awtContent = document.getElementById('awt-report-wdv'),
                weatherContent = document.getElementById('weather-report-wdv'),
                traceTool = document.getElementById('trace-tool'),
                apiTool = document.getElementById('api-tool'),
                showAll = true,
                retryApi = true,
                doMiniCms = false,
                clearedGoing = false,
                clearedAwt = false,
                clearedWeather = false,
                webUiReload = new Array(),
                webUiReloadUrl = null,
                responseError = null,
                extraneousText = '',
                payloadPrompt = '',
                payloadContent = '',
                responseMessage = '',
                statusMessage = '',
                statusLevel = 'none',
                errorMessage = '';
            if (this.readyState === 4) {
                window.its.visualiser.common.LocalLog('XHTTP State 4', window.descartes, 'debug');
                if (this.status === 200) {
                    try {
                        responseData = JSON.parse(this.responseText);
                        process = true;
                    }
                    catch (responseError) {
                        var firstIndex = 0;
                        var lastIndex = this.responseText.length;
                        var tryText = this.responseText.substring(this.responseText.indexOf('{'), this.responseText.lastIndexOf('}'));
                        try {
                            responseData = JSON.parse(tryText);
                            lastIndex = this.responseText.indexOf('{');
                            process = true;
                        }
                        catch (retryError) {
                            statusMessage = 'JASON Parse Error';
                            statusLevel = 'fatal';
                            errorMessage = retryError;
                        }
                        finally {
                            extraneousText = this.responseText.substring(firstIndex, lastIndex);
                        }
                    }
                    if (process) {
                        responseCode = responseData.status;
                        responsePayload = responseData.payload;
                        if (responseCode === 0) {
                            // if the going or weather content is empty, we will need to clear the HMTML
                            if ((goingContent) && (responsePayload.content.goingReport === 0)) {
                                goingContent.outerHTML = '';
                                clearedGoing = true;
                            }
                            if ((awtContent) && (responsePayload.content.awtReport === 0)) {
                                awtContent.outerHTML = '';
                                clearedAwt = true;
                            }
                            if ((weatherContent) && (responsePayload.content.weatherReport === 0)) {
                                weatherContent.outerHTML = '';
                                clearedWeather = true;
                            }
                            // If, on stream update, the going / weather is re-enabled we will need to "reload" the HTML
                            if ((goingContent) && (goingContent.innerHTML.trim().length === 0) && (clearedGoing === false)) {
                                webUiReload.push('Going');
                            }
                            if ((awtContent) && (awtContent.innerHTML.trim().length === 0) && (clearedAwt === false)) {
                                webUiReload.push('AWT');
                            }
                            if ((weatherContent) && (weatherContent.innerHTML.trim().length === 0) && (clearedWeather === false)) {
                                webUiReload.push('Weather');
                            }
                            if (webUiReload.length > 0) {
                                statusMessage = 'Unexpectedly, there is no Content for: ' + webUiReload.join(', ');
                                statusLevel = 'fatal';
                                if (window.allowRetry) {
                                    window.its.visualiser.common.LocalLog('No Content Retry', window.descartes, 'debug');
                                    window.its.visualiser.common.LocalLog(webUiReload, window.descartes, 'debug');
                                    // @note process will be cancelled as page will reload
                                    statusLevel = 'error';
                                    statusMessage+= '. Retrying...';
                                    HelperSetStatus(statusMessage, statusLevel);
                                    webUiReloadUrl = window._buildUrl('webui', 'new-start, newrg, retry');
                                    window._reloadWebUi(webUiReloadUrl);
                                }
                            }
                            window.its.visualiser.common.LocalLog('Update Retrieved OK', window.descartes, 'debug');
                            methodReturn = true;
                        }
                        else {
                            statusLevel = 'none';
                            retryApi = false;
                            showAll = false;
                            doMiniCms = false;
                            switch (responseCode) {
                                case 412:
                                case 496:
                                case 495:
                                    errorMessage = 'Server Response (last update): ' + responseCode + ' - ' + responsePayload.message;
                                    doMiniCms = true;
                                    break;
                                case 490:
                                    var nextRace = responsePayload.message.split('Next Race:')[1];
                                    if (typeof(nextRace) === 'undefined') {
                                        nextRace = 'Not Available';
                                    }
                                    var locationDateHtml = document.getElementById('location-date');
                                    if (locationDateHtml) {
                                        document.getElementById('location-date').innerHTML = nextRace;
                                    }
                                    statusMessage = 'Sorry, but there is no Going Report available at this time. Please try again later. Thank you';
                                    doMiniCms = true;
                                    break;
                                case 491:
                                case 492:
                                    var locationDate = responsePayload.content['location-date'];
                                    var locationDateHtml = document.getElementById('location-date');
                                    locationDate = _locationDate(locationDate, responsePayload.content['going-race-date']);
                                    if (locationDateHtml) { document.getElementById('location-date').innerHTML = locationDate; }
                                    if (responseCode === 491) { statusMessage = responsePayload.content.seasonEndMessage; }
                                    else { statusMessage = 'Unable to Determine the next Race Meeting'; }
                                    doMiniCms = true;
                                    break;
                                default:
                                    if (typeof(responseData.payload) !== 'string') {
                                        // Handle WDV's Capture of PHP Runtime Error
                                        // - An ERROR payload should be an ARRAY as TTITS Error Handling response
                                        //   is an ARRAY of STRINGS
                                        // - The search for "Text" is to remove the specific "error text" from display
                                        // - Will still be available in (Browser) Network View
                                        if (responseData.payload.length >= 1) {
                                            //payloadPrompt = responseData.payload[0];
                                            //payloadContent = responseData.payload[1];
                                            payloadContent = responseData.payload[0];
                                            payloadContent = payloadContent.substr(payloadContent.indexOf('>') + 1);   // still unexplained!
                                            if (payloadContent.indexOf(' Text:') > 0) {
                                                payloadContent = payloadContent.substr(0, payloadContent.indexOf(' Text:'));
                                            }
                                        }
                                        //errorMessage = 'Server Response (last update): ' + responseCode + ' - ' + payloadPrompt + payloadContent;
                                    }
                                    else {
                                        payloadPrompt = 'Application Error::';
                                        payloadContent = responseData.payload;
                                        if (responseCode >= 480) {                   // > 480 != all system errors
                                            // Status 480 is: WDV Stream API has been accessed without a Client
                                            payloadPrompt = '';
                                            payloadContent = 'TurfTrax ITS System Error';
                                        }
                                        statusMessage = responseMessage;
                                    }
                                    statusLevel = 'fatal';
                                    showAll = false;
                                    errorMessage = 'Server Response (last update): ' + responseCode + ' - ' + payloadPrompt + payloadContent;
                                    console.log("Status: " + responseCode + ", Payload: " + payloadPrompt + payloadContent);
                            }
                        }
                        if (responsePayload.hasOwnProperty('content')) {
                            window.lastUpdateContent = responsePayload.content;
                            window.its.visualiser.base.WarningTool.Init();
                        }
                    }
                }
                else {
                    showAll = false;
                    statusLevel = 'fatal';
                    if (this.status >= 100) {
                        statusMessage = 'Server HTTP Status: ' + this.status + ' - ' + this.statusText + ' (' + window.streamApi + ')';
                    }
                    else {
                        // Assume AJAX Aborted
                        statusMessage = 'API Request Timed Out, Server Failed to Respond';
                    }
                }
                if (errorMessage.length > 0) {
                    window.its.visualiser.common.ErrorHalt(errorMessage);
                }
                else if(statusMessage.length > 0) {
                    HelperSetStatus(statusMessage, statusLevel);
                }
                document.body.style.cursor = 'default';
                window.its.visualiser.common.LocalLog('Method Return: ' + methodReturn, window.descartes, 'debug');
                window.its.visualiser.common.LocalLog('Show All: ' + showAll, window.descartes, 'debug');
                window.its.visualiser.common.LocalLog('Retry API: ' + retryApi, window.descartes, 'debug');
                if (methodReturn) {
                    window.haveRetried = 0;
                    window.StartUpdateCountdown();
                    UpdateWDV(responsePayload.content);
                    UpdateMiniCms(responsePayload);
                    window.its.visualiser.common.ShowAllSections();
                    ResizeElements();
                }
                else {
                    if (doMiniCms) {
                        UpdateMiniCms(responsePayload);
                    }
                    if (showAll) {
                        window.its.visualiser.common.ShowAllSections();
                    }
                    if (retryApi) {
                        window._retryApi(statusMessage);
                    }
                    else {
                        window.StartUpdateCountdown(-1);
                    }
                }
                if (traceTool) {
                    var thisContent = '';
                    var thisTool = traceTool.firstElementChild;
                    if (thisTool.classList.contains('menu-icon-blink')) {
                        thisTool.classList.remove('menu-icon-blink');
                    }
                    if (responseData) {
                        if ((responseData.hasOwnProperty('payload')) && (responseData.payload.hasOwnProperty('trace'))) {
                            thisContent = responseData.payload.trace;
                        }
                    }
                    else {
                        thisContent = 'Extraneous Text>>>\n' + extraneousText + '\n<<<\n';
                    }
                    //traceTool.classList.add('menu-icon-blink');
                    window.its.visualiser.base.auditTool.toolContent = thisContent;
                    window.its.visualiser.base.auditTool.Refresh();
                }
                if (apiTool) {
                    var thisContent = '';
                    var thisTool = apiTool.firstElementChild;
                    if (thisTool.classList.contains('menu-icon-blink')) {
                        thisTool.classList.remove('menu-icon-blink');
                    }
                    if (responseData) {
                        thisContent = responseData;
                        if ((responseData.hasOwnProperty('payload')) && (responseData.payload.hasOwnProperty('trace'))) {
                            delete thisContent.payload.trace;
                        }
                    }
                    else {
                        thisContent = 'No API Response Data';
                    }
                    window.its.visualiser.base.apiTool.toolContent = JSON.stringify(thisContent,null,'\t');
                    window.its.visualiser.base.apiTool.Refresh();
                    //apiTool.classList.add('menu-icon-blink');
                }
            }
            return methodReturn;
        };
        streamApiXhttp.open('GET', updateUrl, true);
        streamApiXhttp.setRequestHeader('Content-Type', 'text/plain');
        streamApiXhttp.send();
        window.its.visualiser.common.LocalLog('WDV Update Requested', window.descartes, 'debug');
        return true;
    }
    /**
     * 
     * 
     *  If the content is not to be rendered, the it will be set to <i>skip this</i>
     * @param {type} newContent
     * @returns {Boolean}
     */
    function UpdateWDV(newContent) {
        window.its.visualiser.common.LocalLog('Executing: UpdateWDV', window.descartes, 'debug');
        var contentObject = JSON.parse(JSON.stringify(newContent)),
            contentKeys = Object.keys(contentObject),
            contentLength = contentKeys.length,
            thisName = null,
            thisContent = null,
            actualRainGauge = 'rain' + contentObject.useRainGauge,
            i = null,
            dummy = null;
        HelperSetStatus();                                                      // Clears current Status Message
        for (var i = 0; i < contentLength; i++) {
            thisName = contentKeys[i];
            thisContent = contentObject[thisName];
            if (thisContent === 'No Data') {
                switch (thisName) {
                    case 'status-warning':
                        HelperSetStatus(thisContent);
                        thisContent = window.skipText;
                        break;
                    case 'going-waypoint-map':
                    case 'going-zone-map':
                        var goingMap = document.getElementById('going-map');
                        goingMap.parentNode.innerHTML = '<p id="going-map" style="width:100%; text-align: center;">The Going Map for this Race Meeting is Not Available</p>';
                        if (document.getElementById('wind-repeater')) {
                            document.getElementById('wind-repeater').outerHTML = '';
                        }
                        thisContent = window.skipText;
                        break;
                    default:
                        thisContent = '<span class="no-data-error">' + thisContent + '</span>';
                        break;
                }
            }
            else {
                switch (thisName) {
                    case 'carousel':
                        window.its.visualiser.base.carousel.Init(thisContent);
                        break;
                    case 'windRepeater':
                        window.windRepeater = JSON.parse(thisContent);
                        break;
                    case 'location-date':
                        thisContent = _locationDate(thisContent, newContent['going-race-date']);
                        break;
                    case 'etEnabled':
                        if (thisContent === false) {
                            var etError = contentObject['et-error'];
                            var etMetric = document.getElementById('et-metric');
                            if (etMetric) {
                                document.getElementById('et-metric').outerHTML = '';
                            }
                            window.its.visualiser.common.ShowAdvisory(etError, thisName);
                        }
                        thisContent = window.skipText;
                        break;
                    case 'status-warning':
                        HelperSetStatus(thisContent);
                        thisContent = window.skipText;
                        break;
                    case 'winddirection-current':
                        if (thisContent !== '#') {
                            if (thisContent < 0) {
                                thisContent = thisContent + 360;
                            }
                            if (thisContent >= 360) {
                                thisContent = thisContent - 360;
                            }
                            thisContent = window.its.visualiser.common.MyRound(thisContent, 0);
                        }
                        break;
                    case 'windgust-event':
                        if (thisContent !== window.naText) {
                            thisContent = 'As at ' + thisContent;
                        }
                        thisContent = '(' + thisContent + ')';
                        break;
                    case 'windspeed-average':
                    case 'windspeed-current':
                    case 'windgust-current':
                    case 'windgust-max':
                    case 'windgust-min':
                        // @note scaling factors *3.6 to convert m/s into km/h then *0.6214 to turn km into miles.
                        var scalingFactor = 3.6;
                        if (newContent.units.speed === 'mph') {
                            scalingFactor = scalingFactor * 0.6214;
                        }
                        if (thisContent !== '#') {
                            thisContent = Math.ceil((thisContent * scalingFactor) * 100) / 100;
                        }
                        break;
                    case 'mapping-service':
                        thisContent = window.skipText;
                        break;
                    case 'going-zone-map':
                    case 'going-waypoint-map':
                        var mapType = contentObject['use-map'];
                        var mappingService = contentObject['mapping-service'];
                        if (mappingService !== 'no') {
                            var useMap = 'going-' + mapType + '-map';
                            if (useMap === thisName) {
                                if (thisContent !== '#') {
                                    thisContent = '<img id="going-map" src="' + thisContent + '" alt="Going Map - ' + mapType + '" style="width:100%;">';
                                }
                                else {
                                    thisContent = '<p id="going-map" style="width:100%; text-align: center;">The Going Map for this Race Meeting has not yet been Published</p>';
                                    if (document.getElementById('wind-repeater')) {
                                        document.getElementById('wind-repeater').outerHTML = '';
                                    }
                                }
                            }
                            else {
                                thisContent = window.skipText;
                            }
                        }
                        else {
                                thisContent = window.skipText;
                        }
                        break;
                    case 'use-map':
                        thisContent = window.skipText;
                        break;
                    case 'haveManualRain':
                        window.maunalRain = false;
                        if (thisContent === true) {
                            window.manualRain = true;
                        }
                        break;
                    case 'rain0-today':
                        var donorName = null;
                        // Because we are currently not sending <i>rain0-today</i>, We need to populate it
                        // with whatever the currently selected Rain Gauge is for today / since
                        if ((typeof(contentObject['rain0-today']) === 'string') && (contentObject['rain0-today'].length === 0)) {
                            thisContent = window.skipText;
                            if (contentObject.haveManualRain === true) {
                                if (actualRainGauge === 'rain1') {
                                    donorName = thisName.replace(0, 1);
                                }
                                else if (actualRainGauge === 'rain2') {
                                    donorName = thisName.replace(0, 2);
                                }
                                // ... get donor content and transfer it
                                thisContent = contentObject[donorName];
                                contentObject[thisName] = thisContent;
                            }
                        }
                    case 'rain0-24hr':
                    case 'rain0-7day':
                        if (contentObject.haveManualRain === true) {
                            thisName = thisName.replace('0-', '-');
                        }
                        else {
                            thisContent = window.skipText;
                        }
                        break;
                    case 'rain1-since':
                    case 'rain1-24hr':
                    case 'rain1-7day':
                        if ((actualRainGauge === 'rain1') && (contentObject.haveManualRain === false)) {
                            thisName = thisName.replace(actualRainGauge, "rain");
                        }
                        else {
                            thisContent = window.skipText;
                        }
                        break;
                    case 'rain2-since':
                    case 'rain2-24hr':
                    case 'rain2-7day':
                        if ((actualRainGauge === 'rain2') && (contentObject.haveManualRain === false)) {
                            thisName = thisName.replace(actualRainGauge, "rain");
                        }
                        else {
                            thisContent = window.skipText;
                        }
                        break;
                    case 'seasonEndMessage':
                        HelperSetStatus(thisContent, 'none');
                        thisContent = window.skipText;
                        break;
                }
            }
            // ... refresh the Content
            if (thisContent !== window.skipText) {
                HelperRefreshElement(thisName, thisContent, contentObject);
            }
        }
        window.its.visualiser.base.PostUpdate(newContent);
        return true;
    }
    /**
     * Will resize the Wind Direction Repeater proportionally to the Going Map
     * 
     * It will test if the Repeater is Enabled and the Going Map is displayed
     * 
     * @param {string} surfaceType <i>going</i> or <i>awt</i>
     * @returns {Boolean} TRUE if the resize occurred, FALSE Otherwise
     */
    function ResizeRepeater(surfaceType) {
        window.its.visualiser.common.LocalLog('Executing: ResizeRepeater', window.descartes, 'debug');
        var methodReturn = false;
        var displayMap = surfaceType + '-map';
        var displayRepeater = surfaceType + '-wind-repeater';
        var displayDirection = surfaceType + '-wind-dir-repeat';
        var displayNorth = surfaceType + '-compass-north';
        if (window.windRepeater.hasOwnProperty(surfaceType)) { 
            if ((window.windRepeater[surfaceType].enabled) && (document.getElementById(displayMap)) && (document.getElementById(displayRepeater))){
                var displayImage = document.getElementById(displayMap);
                var displayWidth = displayImage.clientWidth;
                var directionImage = document.getElementById(displayDirection);
                var compassImage = document.getElementById(displayNorth);
                var repeaterDiv = document.getElementById(displayRepeater);
                var widthRatio = displayWidth / window.windRepeater[surfaceType].mapWidth;
                var newRepeaterWidth = Math.ceil(window.windRepeater[surfaceType].repeaterWidth * widthRatio);
                var newDirection = window.windRepeater[surfaceType].deviation;                   // Magnetic deviation -ve = W (anti-clockwise) +ve E (clockwise)
                newDirection = newDirection + window.windRepeater[surfaceType].mapRotation;      // Rotate Map to align with Ground +ve anti-clockwise -ve clockwise
                repeaterDiv.style.width = repeaterDiv.style.height = newRepeaterWidth + 'px';
                repeaterDiv.style.top = Math.ceil(window.windRepeater[surfaceType].divYPos * widthRatio) + displayImage.parentNode.previousElementSibling.clientHeight + 'px';
                repeaterDiv.style.left = Math.ceil(window.windRepeater[surfaceType].divXPos * widthRatio) + 'px';
                directionImage.style.width = compassImage.style.width = newRepeaterWidth + 'px';
                compassImage.style.transform = 'rotate(' + newDirection + 'deg)';
                methodReturn = true;
            }
        }
        if (methodReturn === false) {
            if (document.getElementById(displayRepeater)) {
                document.getElementById(displayRepeater).outerHTML = '';
            }
        }
        return methodReturn;
    }
    /**
     * Will replace the existing HTML Content with that of the last Refresh
     * 
     * Some of the Refresh Content will need additional processing, or will
     * affect / be affected by "other display elements". So that it is done here
     * before passing the content to <i><b>method</b> PaintObect()</i>.
     * 
     * @usedby Method UpdateWDV()
     * 
     * @todo We need to find an "acceptable" way of differentiating between No Data, and Not Supplied by Client
     * 
     * @param {integer} elementId HTML Element ID
     * @param {string} elementContent HTML Content
     * @param {object} contentObject The Stream API Response JSON Packet:content
     * @returns {Boolean} Always TRUE
     */
    function HelperRefreshElement(elementId, elementContent, contentObject) {
        window.its.visualiser.common.LocalLog('Executing: HelperRefreshElement[' + elementId + ']', window.descartes, 'debug');
        var paintObject = document.getElementById(elementId);
        var applyPaint = true;
        var currentContent = null;
        switch (elementId) {
            case 'isDemo':
                var demoContainer = null;
                var demoText = 'WeatherTrax Live Demonstration prepared for ' + contentObject.venueName + '<br>Authorised Use Only';;
                if (document.getElementById('demonstration-notice')) {
                    document.getElementById('demonstration-notice').remove();
                }
                if (elementContent !== false) {
                    if (contentObject.hasOwnProperty('demoText')) {
                        demoText = contentObject.demoText.replace('[HTML_BR]', '<br>');
                    }
                    demoContainer = document.createElement('div');
                    demoContainer.setAttribute('id', 'demonstration-notice');
                    demoContainer.setAttribute('class', 'demonstration-notice');
                    demoContainer.innerHTML = demoText;
                    document.getElementById('header').prepend(demoContainer);
                }
                break;
            case 'additional-comment':
                var moistureContent = HelperGetContent(elementContent,'moisture', '%');
                if (moistureContent.length > 0) {
                    if (!isNaN(moistureContent)) {
                        moistureContent = 'Mean: ' + moistureContent + '%';
                    }
                    var useMoistureEvent = contentObject['going-report-date'];
                    if (window.moistureTakenAt) {
                        useMoistureEvent = window.moistureTakenAt;
                    }
                    if (document.getElementById('additional-full')) {
                        document.getElementById('additional-full').innerHTML = moistureContent;
                        document.getElementById('moisture-event').innerHTML = '(As at ' + useMoistureEvent + ')';
                    }
                }
                break;
            case 'winddirection-current':
                // @note Magnetic Deviation and Map Rotation is not applied to the Metric as direction is relative to North - top of the page
                // @todo Should these sort of calculations be done by the back end? Do we still need values in API?
                // @todo Indicate if compass reading is True or Magnetic
                var num = null;
                var newDirection = null;
                var directionText = '';
                if (!isNaN(elementContent)) {
                    num = parseInt(Number(elementContent - 180));
                    directionText =  'rotate(' + num + 'deg)';
                    elementContent = elementContent + '&deg;';
                }
                if (document.getElementById('wind-dir-icon')) {
                    document.getElementById('wind-dir-icon').style.transform = directionText;
                    document.getElementById('wind-dir-icon').style.visibility = 'visible';
                }
                if (window.windRepeater !== null) {
                    for (var surfaceType in window.windRepeater) {
                        if (document.getElementById(surfaceType + '-wind-dir-repeat')) {
                            newDirection = num + window.windRepeater[surfaceType].deviation;                         // Magnetic deviation -ve = W (anti-clockwise) +ve E (clockwise)
                            newDirection = newDirection + window.windRepeater[surfaceType].mapRotation;              // Rotate Map to align with Ground +ve anti-clockwise -ve clockwise
                            document.getElementById(surfaceType + '-wind-dir-repeat').style.transform = 'rotate(' + newDirection + 'deg)';
                            document.getElementById(surfaceType + '-wind-repeater').style.visibility = 'visible';
                        }
                    }
                }
                break;
            case 'map-orientation':
                if (window.windRepeater !== null) {
                    var num = 0;
                    var newDirection = null;
                    for (var surfaceType in window.windRepeater) {
                        if (document.getElementById(surfaceType + '-wind-dir-repeat')) {
                            document.getElementById(surfaceType + '-compass-north').style.display = 'none';
                            document.getElementById(surfaceType + '-wind-dir-repeat').src = '../assets/images/map-orientation-00.svg';
                            newDirection = num + window.windRepeater[surfaceType].deviation;                         // Magnetic deviation -ve = W (anti-clockwise) +ve E (clockwise)
                            newDirection = newDirection + window.windRepeater[surfaceType].mapRotation;              // Rotate Map to align with Ground +ve anti-clockwise -ve clockwise
                            document.getElementById(surfaceType + '-wind-dir-repeat').style.transform = 'rotate(' + newDirection + 'deg)';
                            document.getElementById(surfaceType + '-wind-repeater').style.visibility = 'visible';
                        }
                    }
                    elementContent = elementContent + '&deg;';
                }
                
                break;
            case 'winddirection-current-rose':
                if ((paintObject) && (paintObject.nodeName.toLowerCase() !== 'img')) {
                    paintObject.style.backgroundPosition = 'right ' + elementContent + 'px top 2px';
                    applyPaint = false;
                }
                break;
            case 'et-error':
                HelperSetStatus('ET Unavailable - ' + elementContent);
                break;
            case 'going-waypoint-map':
            case 'going-zone-map':
                elementId = 'going-map';
                paintObject = document.getElementById(elementId).parentNode;
                break;
            case 'useRainGauge':
                applyPaint = false;
                elementContent = parseInt(elementContent);
                window._viewButton('rg', elementContent);
                if (elementContent > 0) {
                    paintObject = document.querySelector('#rain-metric .metric-source');
                    if (paintObject) {
                        currentContent = paintObject.innerHTML;
                        if (currentContent.toUpperCase().indexOf('(RG') >= 0) {
                            elementContent = currentContent.replace(/\(RG\s+\d+\)/, '(RG ' + elementContent + ')');
                            applyPaint = true;
                        }
                    }
                }
                break;
            case 'haveManualRain':
                applyPaint = false;
                if (elementContent === true) {
                    paintObject = document.querySelector('#rain-metric .metric-source');
                    currentContent = paintObject.innerHTML;
                    if (currentContent.indexOf('Sourced') < 0) {
                        elementContent = paintObject.innerHTML + '<br><span class="much-smaller">(<b>*</b> Sourced from Going Report)</span>';
                        applyPaint = true;
                    }
                }
                break;
            case 'racingToday':
            case 'awtRacingToday':
                paintObject = document.getElementsByClassName('going-report-information')[0];
                if ((typeof(paintObject) !== 'undefined') && (elementContent)) {
                    elementContent = paintObject.innerHTML;
                    elementContent = elementContent.replace('Next Meeting', 'Racing Today');
                }
                else {
                    applyPaint = false;
                }
                break;
            case 'isLastMeeting':
                paintObject = document.getElementsByClassName('going-report-information')[0];
                if ((typeof(paintObject) !== 'undefined') && (elementContent)) {
                    elementContent = paintObject.innerHTML;
                    elementContent = elementContent.replace('Next Meeting', 'Last Meeting');
                }
                else {
                    applyPaint = false;
                }
                break;
            case 'location-track-type':
                if (elementContent === window.naText) {
                    elementContent = '';
                }
                else {
                    elementContent = ' (' + elementContent + ')';
                }
                break;
            case 'stationActivityStatus':
                paintObject = document.getElementById('station-activity-status');
                elementContent = 'Station Update Schedule: &nbsp;' + window._ucFirst(elementContent) + ',&nbsp;';
                break;
            default:
        }
        if (elementContent === '#') {
            elementContent = noDataText;
        }
        if (paintObject && applyPaint) {
            paintObject.innerHTML = elementContent;
        }
        return true;
    }
    /**
     * DEPRECATED in favour of HelperGetContent()
     * 
     * This Method would extract the Soil Moisture from the supplied text
     * 
     * @param {string} elementContent
     * @returns {String} Soil Moisture in the format nn%
     */
    function HelperGetMoisture(elementContent) {
        window.its.visualiser.common.LocalLog('Executing: ' + HelperGetMoisture, window.descartes, 'debug');
        if (elementContent === null) return "";
        var moisturePosition = elementContent.toLowerCase().indexOf('moisture');
        var tmpStr = elementContent.slice(moisturePosition);
        var percentagePos = tmpStr.indexOf('%');
        var moisture = tmpStr.slice(0, percentagePos).replace(/[^0-9.]/g, '');
        return moisture;
    }
    /**
     * Will extract specific text between "markers"
     * 
     * This Method, whilst an improvement on the original HelperGetMoisture is still subject to evolution
     * 
     * @param {type} elementContent
     * @param {type} startMarker
     * @param {type} endMarker
     * @returns {String}
     */
    function HelperGetContent(elementContent, startMarker, endMarker) {
        window.its.visualiser.common.LocalLog('Executing: ' + arguments.callee.name, window.descartes, 'debug');
        var methodReturn = "";
        if (elementContent === null) return methodReturn;
        var startPosition = elementContent.toLowerCase().indexOf(startMarker.toLowerCase());
        var tmpStr = elementContent.slice(startPosition);
        var endPosition = tmpStr.toLowerCase().indexOf(endMarker.toLowerCase());
        if ((startPosition >= 0) && (endPosition >= 0)) {
            if (startMarker.toLowerCase() === 'moisture') {
                var useStringRaw = tmpStr.slice(startMarker.length, endPosition);
                var useString = useStringRaw.toLowerCase();
                var takenMarker = useString.indexOf('taken at');
                if (takenMarker > 0) {
                    var lastSpace = useStringRaw.lastIndexOf(' ');
                    var timeString = useStringRaw.slice(takenMarker + 8, lastSpace);
                    window.moistureTakenAt = timeString;
                }
                methodReturn = useStringRaw.slice(lastSpace, endPosition).replace(/[^0-9.]/g, '');
            }
            else {
                methodReturn = tmpStr.slice(startMarker.length, endPosition).replace(/[^0-9.]/g, '');
            }
        }
        else if ((startPosition >= 0) && (endPosition < 0)) {
            methodReturn = tmpStr.slice(startMarker.length).replace(/^([^a-zA-Z])+/g, '');
        }
        return methodReturn;
    }
    /**
     * Will display a <i>Status Message</i> relelated to the Web Request
     * 
     * If both <i><b>parameters</b> statusContent</i> and <i>statusLevel</i> are omitted, the status message will be cleared
     * If ommitted, the <i><b>parameter</b> statuslevel</i> will default to <i>warning</i>
     * It is intended that a <i>reporting level</i> is implemented to filter the messages.
     * 
     * @see <i><b>property</b> statusPriority</i>
     * @note The Status Message will stay on display until "cleared" on the next Update / Refresh
     * 
     * @param {string} statusContent The Status Message to display
     * @param {string} statusLevel One of: <i>none</i>, <i>info</i>, <i>notice</i>, <i>warning</i>, <i>error</i>, or <i>fatal</i>
     * @returns {Boolean} <b>TRUE</b> If the Status is set, <b>FALSE</b> If the Status is cleared, <b>NULL</b> otherwise
     */
    function HelperSetStatus(statusContent, statusLevel) {
        window.its.visualiser.common.LocalLog('Executing: ' + arguments.callee.name, window.descartes, 'debug');
        var methodReturn = null;
        var statusIndex = null;
        var newHtml = '';
        var newVisibility = 'hidden';
        var statusPrompt = '';
        if ((typeof(statusContent) === 'undefined') && (typeof(statusLevel) === 'undefined')) {
            statusContent = '';                                                 // clear status
            methodReturn = false;
        }
        else {
            if ((typeof(statusContent) !== 'undefined') && (typeof(statusLevel) === 'undefined')) {
                if (window.statusPriority.indexOf(statusContent) < 0) {
                    statusLevel = 'warning';                                    // default is Warning
                }
                else {
                    statusContent = 'Bad Status Status Message: ' + statusContent;
                    statusLevel = 'fatal';
                }
            }
            if ((typeof(statusContent) !== 'undefined') && (typeof(statusLevel) !== 'undefined')){
                statusIndex = window.statusPriority.indexOf(statusLevel);
                if (statusIndex < 0) {
                    statusContent = 'Bad Status Priority trying to Report: ' + statusContent;
                    statusLevel = window.statusPriority.indexOf('fatal');
                }
            }
        }
        if (statusContent.length > 0) {
            if (statusIndex >= window.reportPriority) {
                statusPrompt = '';
                if (statusIndex > 0) {
                    statusPrompt = window._ucFirst(window.statusPriority[statusIndex]) + ': ';
                }
                newHtml = statusPrompt + statusContent;
                newVisibility = 'visible';
                methodReturn = true;
            }
        }
        window.updateStatus.innerHTML = newHtml;
        window.viewStatus.style.visibility = newVisibility;
        return methodReturn;
    }
    /**
     * Will switch between two sets of Readings for the same metric
     * 
     * @todo figure out a way to "prevent" the default copy / paste action on "touch"
     * 
     * @param {type} viewPrefix
     * @param {type} mode
     * @param {type} buttonObject
     * @returns {Boolean}
     */
    function SwapView(viewPrefix, mode, buttonObject) {
        window.its.visualiser.common.LocalLog('Executing: ' + arguments.callee.name, window.descartes, 'debug');
        var currentValue = parseInt(buttonObject.dataset.current);
        var currentIndex = null;
        var nextIndex = null;
        var useIndex = null;
        var useOrdinal = null;
        var useManual = false;
        var listArray = buttonObject.dataset.list.split('|').map(Number);
        if ((mode === 'up') && (window.manualRain === true)) {
            useManual = true;
            window._viewButton('rg', listArray[nextIndex]);
        }
        currentIndex = listArray.indexOf(currentValue);
        nextIndex = currentIndex + 1;
        if (nextIndex >= listArray.length) {
            nextIndex = 0;
        }
        if (mode === 'down') {
            useIndex = nextIndex;
        }
        else {
            useIndex = currentIndex;
        }
        useOrdinal = listArray[useIndex];
        switch (viewPrefix) {
            case 'rg':
                if (useManual) {
                    useOrdinal = 0;
                    window._viewButton('rg', listArray[nextIndex]);
                }
                _getOtherSensor('rain-since', 'rain' + useOrdinal + '-today');
                _getOtherSensor('rain-24hr', 'rain' + useOrdinal + '-24hr');
                _getOtherSensor('rain-7day', 'rain' + useOrdinal + '-7day');
                break;
        }
        return true;
    }
    /**
     * Private Method: Will write into a HTML Element an alternate Reading
     * 
     * @usedby <i><b>method</b> SwapView()</i>
     * 
     * @param {string} readingId DOM ID of Target HTML Element 
     * @param {string} propertyName WDV Update Property Name of "other" Sensor
     * @returns {void}
     */
    function _getOtherSensor(readingId, propertyName) {
        window.its.visualiser.common.LocalLog('Executing: ' + arguments.callee.name, window.descartes, 'debug');
        var otherReading = window.lastUpdateContent[propertyName];
        if (otherReading ==='#') { otherReading = noDataText; }
        document.getElementById(readingId).innerHTML = otherReading;
    }
   
    /**
     * Will get a specific COOKIE
     * 
     * @note Not currently used and is a candidate for DEPRECATION<br>
     *       Was used to get the Rain Gauge preference, so required "force numeric"
     * 
     * @param {string} cookieName
     * @param {boolean} forceNumeric {optional) If <b>TRUE</b> it will parse the value as an <b>INTEGER</b>
     * @returns {integer} The Rain Gauge Number or 0 if none (use default)
     */
    function HelperGetCookie(cookieName, forceNumeric) {
        var foundCookie = window.document.cookie.match('(^|;)\\s*' + cookieName + '\\s*=\\s*([^;]+)'),
            cookieContent = null;
        if (foundCookie) {
            cookieContent = foundCookie.pop();
            if (forceNumeric === true) {
                if (isNaN(cookieContent)) {
                    cookieContent = 0;
                }
                cookieContent = parseInt(cookieContent);
            }
        }
        return cookieContent;
    }
    /**
     * Will Set a specific COOKIE
     * 
     * @note Not currently used and is a candidate for DEPRECATION<br>
     *       Was used to set Rain Gauge preference via Query String
     * 
     * @param {type} cookieName
     * @param {type} cookieContent
     * @param {type} cookieDays
     * @returns {undefined}
     */
    function HelperSetCookie(cookieName, cookieContent, cookieDays) {
        var timeNow = new Date(),
            expiresIn = '';
        timeNow.setTime(timeNow.getTime() + (cookieDays * 24 * 60 * 60 * 1000));
        expiresIn = timeNow.toUTCString();
        document.cookie = cookieName + '=' + cookieContent + '; expires=' + expiresIn + "; path=/";
    }
    /**
     * Private Method: Will capitalise first letter of word
     * 
     * @param {string} content The word to capitalise
     * @returns {string} The capitalised word
     */
    function _ucFirst(content) {
        window.its.visualiser.common.LocalLog('Executing: ' + arguments.callee.name, window.descartes, 'debug');
        var methodReturn = content;
        if (typeof(content) === 'string') {
            content.trim();
            if( (content.length > 0) && (content !== window.naText)) {
                methodReturn = content[0].toUpperCase() + content.slice(1).toLowerCase();
            }
        }
        return methodReturn;
    }
    /**
     * Private Method: will convert CRLF to HTML Br
     * 
     * @note Not currently used, candidate for DEPRECATION
     * 
     * @param {string} content Text to be "converted"
     * @returns {string} The "converted Text
     */
    function _nlBr(content) {
        window.its.visualiser.common.LocalLog('Executing: ' + arguments.callee.name, window.descartes, 'debug');
        var methodReturn = content;
        if ((typeof(content) === 'string') && (content.length > 0) && (content !== window.naText)) {
            methodReturn = content.split("\n").join('<br>');
        }
        return methodReturn;
    }
    /**
     * Will adjust text to fit BOX without SCROLL BARS
     * 
     * This is only executed for Going Display Elements
     * 
     * @uses Window Property compressText to specifically access HTML Element by ID
     * 
     * @note Does not "read" scrollWidth on initial page load because element is<br>
     *       "display:none". So called by GetVisualiserUpdate()
     * 
     * @todo Replace discreet Array with CSS Class
     * 
     * @returns {Boolean} TRUE if exercised, FALSE if not, NULL if there was an Issue
     */
    function HelperRequireCompress() {
        window.its.visualiser.common.LocalLog('Executing: ' + arguments.callee.name, window.descartes, 'debug');
        var candidate = null;
        var useSetting = null;
        var methodReturn = false;
        if ((document.getElementById('going-report-wdv')) || (document.getElementById('awt-report-wdv'))) {
            for (var compressPass in compressText) {
                useSetting = compressText[compressPass];
                for (var i=0; i<compressable.length; i++) {
                    candidate = document.getElementById(compressable[i]);
                    if ((candidate) && (candidate.scrollHeight > candidate.clientHeight)) {
                        candidate.style.fontSize = useSetting.fontSize;
                        candidate.style.lineHeight = useSetting.lineHeight;
                    }
                }
            }
            methodReturn = true;
        }
        return methodReturn;
    }
    /**
     * Wrapper for Resizing Listener
     * 
     * @returns {Boolean} Always TRUE
     */
    function ResizeElements() {
        window.its.visualiser.common.LocalLog('Executing: ' + arguments.callee.name, window.descartes, 'debug');
        ResizeRepeater('going');
        ResizeRepeater('awt');
        HelperRequireCompress();
        return true;
    }
    /**
     * Will Hide or Show the Mini-CMS Menu
     * 
     * @param {boolena} forceClose [optional, default is <i>undefined</i>] If set <b>TRUE</b> the mini-cms menu will be closed
     * @returns {Boolean} <b>TRUE</b> If the mini-cms menu is displayed, <b>FALSE</b> otherwise.
     */
    function ToggleMiniCms(forceClose) {
        window.its.visualiser.common.LocalLog('Executing: ' + arguments.callee.name, window.descartes, 'debug');
        var methodReturn = false;
        var targetId = 'api-mini-cms';
        var target = document.getElementById(targetId);
        var toolUsed = document.getElementById(targetId + '-tool');
        var mode = target.style.display;
        if (forceClose === true) {
            mode = 'block';
        }
        clearTimeout(window.cmsPopupTimer);
        switch (mode) {
            case 'none':
                target.style.display = 'block';
                toolUsed.title = 'Click to hide Mini-CMS';
                window.cmsPopupTimer = setTimeout(window.ToggleMiniCms, window.cmsPopupInterval, true);
                methodReturn = true;
                break;
            default:
                target.style.display = 'none';
                toolUsed.title = 'Click to show Mini-CMS';
                break;
        }
        if (window.its.visualiser.common.License.haveTTSVC === 'wdv_overview') {
            window.top.its.overview.ResizeFrame('wdv-' + window.clientName + '-frame');
        }
        return methodReturn;
    }
    /**
     * Will update the API Setting Menu on Update / Refresh
     * 
     * @todo Automate this. I.e. have list of mini-cms things and iterate it
     * 
     * @param {object} payloadObject The latest Stream API Response
     * @returns {Boolean} Always <b>TRUE</b>
     */
    function UpdateMiniCms(payloadObject) {
        window.its.visualiser.common.LocalLog('Executing: ' + arguments.callee.name, window.descartes, 'debug');
        var methodReturn = false;
        var intermediate = null;
        var useValue = null;
        var haveMiniCms = document.getElementById('api-mini-cms-version');
        if (haveMiniCms) {
            document.getElementById('api-mini-cms-version').innerHTML = payloadObject.header.signature;
            document.getElementById('api-mini-cms-mappping').innerHTML = window._ucFirst(payloadObject.content['mapping-service']);
            document.getElementById('api-mini-cms-track').innerHTML = payloadObject.content.trackType;
            useValue = window.naText;
            if (payloadObject.content.trackType !== 'AWT') {
                if (payloadObject.content.hasOwnProperty('usingReport')) {useValue = payloadObject.content.usingReport;}
                document.getElementById('api-mini-cms-report').innerHTML = useValue;
                document.getElementById('api-mini-cms-map').innerHTML = window._ucFirst(payloadObject.content['use-map']);
                document.getElementById('api-mini-cms-mapname').innerHTML = payloadObject.content['mapName'];
                useValue = 'Most Recent';
                intermediate = payloadObject.tardis['only-published'];
                if (intermediate) {useValue = 'Published';}
                document.getElementById('api-mini-cms-display').innerHTML = useValue;
                useValue = 'For ' + payloadObject.tardis['days-before']['calendar'] + ' day(s) before and ' + payloadObject.tardis['days-after']['calendar'] + ' day(s) after';
                intermediate = payloadObject.tardis['display-always'];
                if (intermediate) {useValue = 'Continually displayed';}
                document.getElementById('api-mini-cms-when').innerHTML = useValue;
            }
            else {
                document.getElementById('api-mini-cms-report').innerHTML = useValue;
                document.getElementById('api-mini-cms-map').innerHTML = useValue;
                document.getElementById('api-mini-cms-mapname').innerHTML = useValue;
                document.getElementById('api-mini-cms-display').innerHTML = useValue;
                document.getElementById('api-mini-cms-when').innerHTML = useValue;
            }
            useValue = window.naText;
            if (payloadObject.content.hasOwnProperty('usingAwtReport')) {useValue = payloadObject.content.usingAwtReport;}
            document.getElementById('api-mini-cms-awt-report').innerHTML = useValue;
            if (payloadObject.content.hasOwnProperty('awtMapName')) {useValue = payloadObject.content.awtMapName;}
            document.getElementById('api-mini-cms-awt-mapname').innerHTML = useValue;
            document.getElementById('api-mini-cms-type').innerHTML = payloadObject.content.stationType;
            useValue = '&nbsp;';
            intermediate = parseInt(payloadObject.content.useRainGauge);
            if ((isNaN(intermediate)) || (intermediate <=0)) {
                useValue = payloadObject.content.useRainGauge;
            }
            document.getElementById('api-mini-cms-rg').innerHTML = useValue;
            window._setCmsButton('userg', payloadObject, 'init');
            window._setCmsButton('setrg', payloadObject, 'init');
            methodReturn = true;
        }
        return methodReturn;
    }
    
    function ButtonAction(takeAction, buttonObject) {
        window.its.visualiser.common.LocalLog('Executing: ButtonAction', window.descartes, 'debug');
        var refreshRequired = true;
        var closeMenu = true;
        var newLocation = null;
        document.body.style.cursor = 'progress';
        switch (takeAction.toLowerCase()) {
            case 'update-2':                                                    // Tool Bar Activation
                closeMenu = false;                                              // We don't want to close the mini-CMS
            case 'update-1':                                                    // mini-CMS Activation 
                if (buttonObject.dataset.isButton) {
                    buttonObject = document.getElementById(buttonObject.dataset.isButton);
                    //closeMenu = true;                                         // Need to stop this action opening CMS but this is not enough
                }
                window._blinkIcon(buttonObject);
                newLocation = window._buildUrl('api', 'new-start');
                break;
            case 'reload':
                window._blinkIcon(buttonObject);
                newLocation = window._buildUrl('webui', 'manual');
                buttonObject.disabled = true;
                buttonObject.style.cursor = 'wait';
                window._reloadWebUi(newLocation, -3);
                return true;
                break;
            case 'userg':
                newLocation = window._buildUrl('api', 'new-start');
                newLocation = window._addParam(newLocation, 'userg', buttonObject.value);
                break;
            case 'setrg':
                var setResponse = null;
                var setKey = _getKey('type', takeAction);
                if (setKey) {
                    buttonObject.style.cursor = 'wait';
                    setResponse = window.its.settings.SetConfig(setKey + ',' + takeAction, buttonObject.value, window.CmsResponse);
                    // @note <i><b>method</b> CmsResponse()</i> will Handle things from here. Except for:
                    if (setResponse !== true) {
                        var lastError = window.its.settings.GetLastError();
                        var errorMessage = lastError.message;
                        if (lastError.severity.toLowerCase() === 'fatal') {
                            errorMessage+= '<br>Please contact Turftrax Support. Thank you.';
                        }
                        else if (lastError.severity.toLowerCase() === 'critical') {
                            newLocation = window._buildUrl('webui', 'new-start');
                            window._reloadWebUi(newLocation);
                            errorMessage+= '<br>This Page will be automatically re-loaded';
                        }
                        HelperResponseError(errorMessage, takeAction);
                    }
                }
                refreshRequired = false;                                        // Inhibit automatic page re-load.
                closeMenu = false;                                              // We do not to close the menu at this time.
                break;
            case 'uat-link':
                var reportId = window.lastUpdateContent.usingAwtReport;
                var hubLink = 'http://hub-uat.turftrax.co.uk/going-report';     // until we fix the https issue
            case 'hub-link':
                if (typeof(reportId) === 'undefined') {
                    var reportId = window.lastUpdateContent.usingReport;
                }
                if (typeof(hubLink) === 'undefined') {
                    var hubLink = 'http://hub.turftrax.co.uk/going-report';     // until we fix the https issue
                }
                var venueId = parseInt(window.lastUpdateContent.venueId);
                if (reportId === window.naText) {
                    
                    hubLink+= '?course=' + venueId;
                }
                else if (Number.isInteger(parseInt(reportId))) {
                    hubLink+='/' + reportId + '/edit';
                }
                window.open(hubLink, 'tt-hub-link');
                refreshRequired = false;
                break;
            case 'defaultRg':
                refreshRequired = false;
                break;
        }
        if (refreshRequired) {
            clearTimeout(window.updateTimer);
            window.updateCountdown.innerHTML = window.updateInterval;
            GetVisualiserUpdate(newLocation);
        }
        if (closeMenu) {
            setTimeout(ToggleMiniCms, 500);                                     // At least 500ms - gives JS time to "process"
        }
        return true;
    }
    
    function ResetPopup(popupObject) {
        window.its.visualiser.common.LocalLog('Executing: ResetPopup', window.descartes, 'debug');
        var methodReturn = false;
        var popupId = popupObject.parentNode.id;
        if (document.getElementById(popupId)) {
            switch (popupId) {
                case 'api-mini-cms':
                    clearTimeout(window.cmsPopupTimer);
                    window.cmsPopupTimer = setTimeout(window.ToggleMiniCms, window.cmsPopupInterval, true);
                    break;
            }
            methodReturn = true;
        }
        return methodReturn;
    }
    /**
     * CallBack: Will handle Mini-CMS Requests
     * 
     * @param {object} ajaxObject CMS Action AJAX Respone
     * @param {string} actionTaken CMS Action Requested
     * @returns {Boolean}
     */
    function CmsResponse(ajaxObject, actionTaken) {
        window.its.visualiser.common.LocalLog('Executing: CmsResponse', window.descartes, 'debug');
        var methodReturn = false;
        var responseData = null;
        var process = false;
        var statusCode = null;
        var errorMessage = '';
        var errorSeverity = '';
        var acceptStatusCodes = [496, 495, 306, 497];
        var newLocation = null;
        var success = false;
        if (ajaxObject.status === 200) {
            try {
                responseData = JSON.parse(ajaxObject.responseText);
                process = true;
            }
            catch (responseError) {
                var tryText = ajaxObject.responseText.substring(ajaxObject.responseText.indexOf('{'), ajaxObject.responseText.lastIndexOf('}'));
                if (tryText.length > 0) {
                    try {
                        responseData = JSON.parse(tryText);
                        process = true;
                    }
                    catch (retryError) {
                        statusCode = 341;                                           // this is actually a Mezurit Code, but it's appropriate
                        errorMessage = 'JSON Parse Error';
                    }
                }
                else {
                    statusCode = 344;
                    errorMessage = 'Returned Data was not what was expected: ' + ajaxObject.responseText;
                }
            }
            if (process === true) {
                if (responseData.hasOwnProperty('message')) {
                    errorMessage = responseData.message;
                }
                else if ((responseData.hasOwnProperty('status')) && (responseData['status'] > 0)) {
                    statusCode = responseData['status'];
                    errorMessage = responseData.payload;
                }
                else {
                    statusCode = responseData['status'];
                }
            }
            if (errorMessage.length > 0) {
                if (acceptStatusCodes.includes(statusCode) === false) {
                    errorSeverity = 'fatal';
                }
                HelperResponseError(errorMessage, actionTaken, errorSeverity);
            }
            else {
                success = true;
            }
            if ((success) || (statusCode === 496)) {
                newLocation = window._buildUrl('api', 'new-start, newrg');
                clearTimeout(window.updateTimer);
                window.GetVisualiserUpdate(newLocation);                        // Get New Update immediately
                methodReturn = true;
            }
        }
        else {
            errorMessage = ajaxObject.statusText;
            if (ajaxObject.status >= 500) {
                errorSeverity = 'fatal';
            }
            HelperResponseError(errorMessage, actionTaken, errorSeverity);
        }
        // ensure all our cursors are as they should be
        document.body.style.cursor = 'default';
        var cleanupList = document.getElementsByClassName('mini-cms-button');
        for (var i=0;i<cleanupList.length;i++) {
            if (cleanupList[i].style.cursor === 'wait') {
                cleanupList[i].style.cursor = 'pointer';
            }
        }
        return methodReturn;
    }
    /**
     * Private Method: Will configure the Min-CMS Set Buttons
     * 
     * @param {string} buttonType The Button Group e.g. <i>userg</b>
     * @param {object} responsePayload The Stream API Response <i>content</i>
     * @param {string} mode One of:<br>
     *     <i>init</i> Sets Buttons in their Intial State
     * @returns {Boolean} <b>TRUE</b> if the Buttons were Set, <b>FALSE</b> otherwise
     */
    function _setCmsButton(buttonType, responsePayload, mode) {
        window.its.visualiser.common.LocalLog('Executing: _setCmsButton', window.descartes, 'debug');
        var methodReturn = false;
        var toUse = responsePayload.content.useRainGauge;
        var activeId = 'api-mini-cms-' + buttonType + toUse;
        var setButton = [];
        var attributeSet = {};
        var buttonList = null;
        var processButton = true;
        var activeButton = document.getElementById(activeId);
        if (activeButton) {
            if ((responsePayload.content.haveManualRain === true) && (buttonType === 'userg')) {
                // Manual Rain Data - "use buttons" are a bit academic 
                activeButton.parentNode.innerHTML = '<span class="manual-override">Manual readings collected from the Going Report</span>';
                processButton = false;
            }
            if (processButton) {
                buttonList = activeButton.parentNode.getElementsByTagName('button');
                attributeSet = {
                    'cursor': {
                        'off': 'not-allowed',
                        'on': 'pointer'
                    },
                    'disabled': {
                        'off': false,
                        'on': true
                    }
                };
                setButton = ['off', 'on'];
                if (mode === 'init') {
                    setButton = ['on', 'off'];
                }
                for (var i=0; i<buttonList.length; i++) {
                    var thisButton = document.getElementById(buttonList[i].id);
                    if (thisButton.id === activeId) {
                        // enable THIS Button
                        thisButton.style.cursor = attributeSet.cursor[setButton[1]];
                        thisButton.disabled = attributeSet.disabled[setButton[0]];
                    }
                    else if (thisButton.innerHTML.indexOf('Default') > 0) {
                        // For the moment, skip any "default" Buttons
                    }
                    else {
                        // disable ALL Others
                        thisButton.style.cursor = attributeSet.cursor[setButton[0]];
                        thisButton.disabled = attributeSet.disabled[setButton[1]];
                    }
                }
            }
            methodReturn = true;
        }
        return methodReturn;
    }
    
    function HelperResponseError(messageText, caller, severity) {
        window.its.visualiser.common.LocalLog('Executing: ResponseError', window.descartes, 'debug');
        var targetElement = document.getElementById('api-error-' + caller);
        var rider = '';
        if (severity === 'fatal') {
            rider = '<br>Please contact Turftrax Support. Thank you.';
        }
        if (messageText.length > 0) {
            targetElement.innerHTML = messageText + rider;
            targetElement.style.display = 'block';
            setTimeout(HelperResponseError, window.errorInterval, '', caller);
        }
        else {
            targetElement.innerHTML = '';
            targetElement.style.display = 'none';
        }
    }
    /**
     * Private Method: Will get the ITS Configuration Property for an API Setting
     * 
     * On Error, an appropriate message will be displayed in the <i>action response</i> Element
     * 
     * @param {string} idMarker The <i>api setting</i> "group" e.g <i>Going Map</i>, <i>Rain Gauges</i>, <i>Actions</i> etc
     * @param {string} actionTaken The <i>set action</i> as passed to <i><b>method</b> ButtonAction()</i>
     * @returns {String|Boolean} On success, the Confgiuration Property, <b>FALSE</b> otherwise
     */
    function _getKey(idMarker, actionTaken) {
        window.its.visualiser.common.LocalLog('Executing: _getKey', window.descartes, 'debug');
        var methodReturn = false;
        var errorMessage = '';
        var tryMarker = idMarker.toLowerCase();
        var tryId = null;
        var haveElement = null;
        var keyValue = null;
        tryId = 'api-mini-cms-' + tryMarker;
        haveElement = document.getElementById(tryId);
        if (haveElement) {
            switch (tryMarker) {
                case 'type':
                    keyValue = haveElement.innerHTML.toLowerCase();
                    keyValue = keyValue.replace('(dual)','').trim();
                    if (keyValue === 'wtx') {
                        methodReturn = 'weatherReportWtx';
                    }
                    else if (keyValue === 'deltat') {
                        methodReturn = 'weatherReport';
                    }
                    else {
                        errorMessage = 'Unable to Identify Station Type';
                    }
                    break;
                default:
                    errorMessage = 'No Action has been defined for <b>' + idMarker + '</b>';
            }
        }
        else {
            errorMessage = 'Bad Key Marker';
        }
        if (errorMessage.length > 0) {
            HelperResponseError(errorMessage, actionTaken, 'fatal');
        }
        return methodReturn;
    }
    /**
     * Private Method: Will modify the Sensor View Button with the Alternate Sensor
     * 
     * @note For Historical reasons <i>Rain Group</i> is referred to as <i>rg</i>
     * @param {string} viewSuffix The Sensor "Group" e.g. <i>rg</i>, <i>temperature</i>, <i>windspeed</i> etc
     * @param {integer} activeSensor The ordinal number of the Sensor actively Viewed
     * @returns {Boolean} <b>TRUE</b> if the View Button Exists, <b>FALSE</b> otherwise
     */
    function _viewButton(viewSuffix, activeSensor) {
        window.its.visualiser.common.LocalLog('Executing: _viewButton', window.descartes, 'debug');
        var methodReturn = false;
        var target = document.getElementById('view-' + viewSuffix);
        var currentIndex = null;
        var nextIndex = null;
        var listArray = new Array();
        if (target) {
            listArray = target.dataset.list.split('|').map(Number);
            currentIndex = listArray.indexOf(activeSensor);
            nextIndex = currentIndex + 1;
            if (nextIndex >= listArray.length) {
                nextIndex = 0;
            }
            target.title = target.title.replace(listArray[currentIndex], listArray[nextIndex]);
            target.innerHTML = target.innerHTML.replace(listArray[currentIndex], listArray[nextIndex]);
            target.dataset.current = listArray[currentIndex];
            target.style.visibility = 'visible';
            methodReturn = true;
        }
        return methodReturn;
    }
    /**
     * Private Method: Will build a "clean" URL
     * 
     * Will add Required Parameters e.g. <i>mode</i>
     * 
     * @param {string} accessMode One of <i>api</i> or <i>webui</i>
     * @param {array} searchList An array of:<br>
     *      <i>newrg</i> - Will force Rain Gauge selection as per WDV configuration<br>
     *      <i>new-start</i> - Will mark the WDV Query Cache as 'dirty'<br>
     *      <i>retry</i> - Will prevent further Page Reload attempts
     * @returns {string} The constructed URL
     */
    function _buildUrl(accessMode, searchList) {
        window.its.visualiser.common.LocalLog('Executing: _buildUrl', window.descartes, 'debug');
        var methodReturn = null;
        var searchArray = new Array();
        var usePath = '';
        var newQuery = '';
        var glue = '?';
        var licenseMe = '';
        if (window.its.visualiser.common.License.inFrame) {
            var licenseMe = "_ttema=" + window.its.visualiser.common.License.haveTTEMA;
            licenseMe+= "&_ttsvc=" + window.its.visualiser.common.License.haveTTSVC;
        }
        if (accessMode === 'api') {
            usePath = window.streamApi + window.clientName + '.html';
        }
        else if (accessMode === 'webui') {
            usePath = '/visualiser/' + window.clientName + '/';
        }
        methodReturn = location.origin + usePath;
        if (usePath.length > 0) {
            // ... do required params first
            if (window.runMode) {
                newQuery+= glue + 'mode=' + window.runMode;
                glue = '&';
            }
            if (typeof(searchList) === 'string') {
                searchList = searchList.replace(/\s/g, '');
                if (searchList.length > 0) {
                    searchArray = searchList.split(',');
                    newQuery+= glue + searchArray.join('=yes&') + '=yes';
                }
            }
            if (licenseMe.length > 0) {
                newQuery+= glue + licenseMe;
            }
            methodReturn+= newQuery;
        }
        window.its.visualiser.common.LocalLog('Returning URL: ' + methodReturn, window.descartes, 'debug');
        return methodReturn;
    }
    /**
     * Private Method: Will add a Name/Value Pair to a URL
     * 
     * @param {string} thisUrl Initial URL
     * @param {string} name Parameter Name
     * @param {string} value Parameter Value
     * @returns {String} Modified URL
     */
    function _addParam(thisUrl, name, value) {
        window.its.visualiser.common.LocalLog('Executing: _addParam', window.descartes, 'debug');
        var glue = '?';
        if (thisUrl.indexOf(glue) > 0) {
            glue = '&';
        }
        return thisUrl + glue + name + '=' + value;
    }
    /**
     * Private Method: Will retry the connection to the Stream API
     * 
     * It works by calling <i><b>method</b> StartUpdateCountdown()</i> with a modified
     * count, as determined by <i><b>property</b> retryUpdate</i>. It will make as many
     * attempts to re-connect, as determined by <i><b>property</b> retryCount</i>, using
     * <i><b>property</b> haveRetried</i> as an intermediate counter.
     * 
     * @param {string} statusMessage Typically the "original" Error Message
     * @returns {void}
     */
    function _retryApi(statusMessage) {
        window.its.visualiser.common.LocalLog('Executing: _retryApi', window.descartes, 'debug');
        var retriesRemaining = window.retryCount;
        clearTimeout(window.responseTimer);
        clearTimeout(window.updateTimer);
        window.haveRetried++;
        retriesRemaining = window.retryCount - window.haveRetried;
        if (window.haveRetried <= window.retryCount) {
            HelperSetStatus(statusMessage + ' - Attempting Retry (' + retriesRemaining + ' remaining)', 5);
            window.StartUpdateCountdown(window.retryUpdate);
        }
        else {
            window.StartUpdateCountdown();
        }
    }
    /**
     * Private Method: Will reload the Page after an optional delay
     * 
     * If no delay time is provided, or it equates to 0 (<i>parseInt()</i> then the
     * page will reload after 5 seconds to allow completion / intervention.
     * @note This "minimum delay" will <b>be added</b> to <i><b>parameter</b> delaySeconds</i>
     * 
     * @param {string} newHref The new Location HREF, with appropriate Search Parameters
     * @param {integer} delaySeconds Delay <i>n</i> seconds before reloading. 
     * @returns {void}
     */
    function _reloadWebUi(newHref, delaySeconds) {
        window.its.visualiser.common.LocalLog('Executing: _reloadWebUi', window.descartes, 'debug');
        var delayInterval = null;
        var minDelay = 5;
        window.its.visualiser.base.auditTool.Destroy();
        window.its.visualiser.base.apiTool.Destroy();
        if (typeof(delaySeconds) === 'undefined') {
            delaySeconds = 0;
        }
        delaySeconds = parseInt(delaySeconds);
        delayInterval = (minDelay + delaySeconds) * 1000;
        setTimeout(function () {location.href=newHref;}, delayInterval);
    }
    
    function _blinkIcon(iconObject, stayOn) {
        window.its.visualiser.common.LocalLog('Executing: _blinkIcon', window.descartes, 'debug');
        var methodReturn = false;
        if (iconObject) {
            if (iconObject.classList.contains('menu-icon-blink')) {
                iconObject.classList.remove('menu-icon-blink');
            }
            else {
                iconObject.classList.add('menu-icon-blink');
                if (stayOn !== true) {
                    setTimeout(window._blinkIcon, 1000, iconObject);
                }
            }
            mehodReturn = true;
        }
        return methodReturn;
    }
    
    function _locationDate(thisContent, raceDate) {
        window.its.visualiser.common.LocalLog('Executing: _locationDate', window.descartes, 'debug');
        var locationDate = thisContent;
        if (thisContent === naText) {
            locationDate = 'Not currently Available';
        }
        else if ((thisContent === 'Next Season') && (raceDate !== window.naText)) {
            locationDate = locationDate + ', starts ' + raceDate;
        }
        return locationDate;
    }