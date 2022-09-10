:{
let
    target =
          Target {oName = "plotter",   -- A friendly name for the target (only used in error messages)
                  oAddress = "localhost", -- The target's network address, normally "localhost"
                  oPort = 57121,           -- The network port the target is listening on
                  oLatency = 0,         -- Additional delay, to smooth out network jitter/get things in sync
                  oSchedule = Live,       -- The scheduling method - see below
                  oWindow = Nothing,      -- Not yet used
                  oHandshake = False,     -- SuperDirt specific
                  oBusPort = Nothing      -- Also SuperDirt specific
                 }
    oscplay = OSC "/plot" $ ArgList [("x", Nothing),
                                     ("y", Nothing)
                                     ]
    oscplay_named_params = OSC "/play" Named {requiredArgs = ["x", "y", "c"]}
    oscmap = [(target, [oscplay_named_params])]
:}

stream <- startStream defaultConfig oscmap

:{
let
    x1 = streamReplace stream 1
    x2 = streamReplace stream 2
    x3 = streamReplace stream 3
    x4 = streamReplace stream 4
    x5 = streamReplace stream 5
    x6 = streamReplace stream 6
    phush = streamHush stream
    x = pF "x"
    y = pF "y"
    c = pS "c"
    xy x_ y_ = (x x_) |>| (y y_)
    yx y_ x_ = (y y_) |>| (x x_)
    circle x_ y_ rad rate = xy (range (x_+2*rad) (x_) $ f rate sine)
                               (range (y_+2*rad) (y_) $ f rate cosine)
:}
