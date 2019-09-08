# -*- coding: utf-8 -*- 

###########################################################################
## Python code generated with wxFormBuilder (version Jun 17 2015)
## http://www.wxformbuilder.org/
##
## PLEASE DO "NOT" EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc

###########################################################################
## Class TsFrame
###########################################################################

class TsFrame ( wx.Frame ):
	
	def __init__( self, parent ):
		wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = u"Turbidostat", pos = wx.DefaultPosition, size = wx.Size( 478,650 ), style = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )
		
		self.SetSizeHintsSz( wx.Size( 434,650 ), wx.Size( -1,-1 ) )
		self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_MENU ) )
		
		bSizer2 = wx.BoxSizer( wx.VERTICAL )
		
		self.m_notebook = wx.Notebook( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0, u"settings" )
		self.m_notebook.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOW ) )
		
		self.m_pnlSettings = wx.Panel( self.m_notebook, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL, u"settings" )
		self.m_pnlSettings.SetForegroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOWTEXT ) )
		self.m_pnlSettings.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_MENU ) )
		
		fgSizerSuper = wx.FlexGridSizer( 4, 1, 0, 0 )
		fgSizerSuper.SetFlexibleDirection( wx.BOTH )
		fgSizerSuper.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )
		
		sbSizerConnection = wx.StaticBoxSizer( wx.StaticBox( self.m_pnlSettings, wx.ID_ANY, u"Connection" ), wx.VERTICAL )
		
		fgSizerConnection = wx.FlexGridSizer( 0, 4, 0, 0 )
		fgSizerConnection.SetFlexibleDirection( wx.BOTH )
		fgSizerConnection.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )
		
		self.m_txtPort = wx.StaticText( sbSizerConnection.GetStaticBox(), wx.ID_ANY, u"Port:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtPort.Wrap( -1 )
		self.m_txtPort.SetForegroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOWTEXT ) )
		
		fgSizerConnection.Add( self.m_txtPort, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		self.m_tcPort = wx.TextCtrl( sbSizerConnection.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_tcPort.SetMinSize( wx.Size( 150,-1 ) )
		
		fgSizerConnection.Add( self.m_tcPort, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		self.m_btnConnect = wx.Button( sbSizerConnection.GetStaticBox(), wx.ID_ANY, u"connect", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_btnConnect.SetToolTipString( u"Connect to the Turbidostat" )
		
		fgSizerConnection.Add( self.m_btnConnect, 0, wx.ALL, 5 )
		
		self.m_bitmConnected = wx.StaticBitmap( sbSizerConnection.GetStaticBox(), wx.ID_ANY, wx.Bitmap( u"res/disconnected.png", wx.BITMAP_TYPE_ANY ), wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizerConnection.Add( self.m_bitmConnected, 0, wx.ALL, 5 )
		
		
		sbSizerConnection.Add( fgSizerConnection, 1, wx.EXPAND, 5 )
		
		
		fgSizerSuper.Add( sbSizerConnection, 1, wx.EXPAND, 5 )
		
		sbSizerOD = wx.StaticBoxSizer( wx.StaticBox( self.m_pnlSettings, wx.ID_ANY, u"Optical Density (at 650nm)" ), wx.VERTICAL )
		
		fgSizerOD = wx.FlexGridSizer( 3, 4, 0, 0 )
		fgSizerOD.SetFlexibleDirection( wx.BOTH )
		fgSizerOD.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )
		
		self.m_txtODText = wx.StaticText( sbSizerOD.GetStaticBox(), wx.ID_ANY, u"OD:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtODText.Wrap( -1 )
		fgSizerOD.Add( self.m_txtODText, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		self.m_txtOD = wx.StaticText( sbSizerOD.GetStaticBox(), wx.ID_ANY, u"n/A", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtOD.Wrap( -1 )
		self.m_txtOD.SetToolTipString( u"The optical density of the medium in the beam path" )
		self.m_txtOD.SetMinSize( wx.Size( 60,-1 ) )
		
		fgSizerOD.Add( self.m_txtOD, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		self.m_btnSetI0 = wx.Button( sbSizerOD.GetStaticBox(), wx.ID_ANY, u"set I_0", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_btnSetI0.SetToolTipString( u"Set the Intensity Baseline for an empty test tube" )
		
		fgSizerOD.Add( self.m_btnSetI0, 0, wx.ALL, 5 )
		
		
		fgSizerOD.AddSpacer( ( 0, 0), 1, wx.EXPAND, 5 )
		
		self.m_txtOD1cmText = wx.StaticText( sbSizerOD.GetStaticBox(), wx.ID_ANY, u"OD(1cm):", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtOD1cmText.Wrap( -1 )
		fgSizerOD.Add( self.m_txtOD1cmText, 0, wx.ALL, 5 )
		
		self.m_txtOD1cm = wx.StaticText( sbSizerOD.GetStaticBox(), wx.ID_ANY, u"n/A", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtOD1cm.Wrap( -1 )
		self.m_txtOD1cm.SetToolTipString( u"The optical density of the medium with an hypothetical path length of 10mm" )
		
		fgSizerOD.Add( self.m_txtOD1cm, 0, wx.ALL, 5 )
		
		
		fgSizerOD.AddSpacer( ( 0, 0), 1, wx.EXPAND, 5 )
		
		
		fgSizerOD.AddSpacer( ( 0, 0), 1, wx.EXPAND, 5 )
		
		self.m_txtTargetODText = wx.StaticText( sbSizerOD.GetStaticBox(), wx.ID_ANY, u"Target OD:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtTargetODText.Wrap( -1 )
		fgSizerOD.Add( self.m_txtTargetODText, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		self.m_tcTargetOD = wx.TextCtrl( sbSizerOD.GetStaticBox(), wx.ID_ANY, u"23.54", wx.DefaultPosition, wx.DefaultSize, wx.TE_CENTRE )
		self.m_tcTargetOD.SetMaxLength( 0 ) 
		self.m_tcTargetOD.SetToolTipString( u"The desired optical density" )
		
		fgSizerOD.Add( self.m_tcTargetOD, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		self.m_btnSetTargetOD = wx.Button( sbSizerOD.GetStaticBox(), wx.ID_ANY, u"&set", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_btnSetTargetOD.SetDefault() 
		self.m_btnSetTargetOD.SetToolTipString( u"Set the desired optical density" )
		
		fgSizerOD.Add( self.m_btnSetTargetOD, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		
		sbSizerOD.Add( fgSizerOD, 1, wx.EXPAND, 5 )
		
		
		fgSizerSuper.Add( sbSizerOD, 1, wx.EXPAND, 5 )
		
		sbSizerPump = wx.StaticBoxSizer( wx.StaticBox( self.m_pnlSettings, wx.ID_ANY, u"Pump" ), wx.VERTICAL )
		
		gSizerPump = wx.GridSizer( 5, 4, 0, 0 )
		
		m_rbPumpModeChoices = [ u"automatic", u"manual" ]
		self.m_rbPumpMode = wx.RadioBox( sbSizerPump.GetStaticBox(), wx.ID_ANY, u"Pump mode", wx.DefaultPosition, wx.DefaultSize, m_rbPumpModeChoices, 2, wx.RA_SPECIFY_COLS )
		self.m_rbPumpMode.SetSelection( 0 )
		self.m_rbPumpMode.SetToolTipString( u"The automatic pump mode pump in pulses until the target OD has been reached. The manual pump mode allows to switch the pump on manually." )
		
		gSizerPump.Add( self.m_rbPumpMode, 0, wx.ALL, 5 )
		
		
		gSizerPump.AddSpacer( ( 0, 0), 1, wx.EXPAND, 5 )
		
		self.m_txtManualPump = wx.StaticText( sbSizerPump.GetStaticBox(), wx.ID_ANY, u"Manual pump:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtManualPump.Wrap( -1 )
		gSizerPump.Add( self.m_txtManualPump, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		self.m_tbManualPump = wx.ToggleButton( sbSizerPump.GetStaticBox(), wx.ID_ANY, u"off", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_tbManualPump.SetToolTipString( u"Turn the pump on and off" )
		
		gSizerPump.Add( self.m_tbManualPump, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		self.m_txtPumpInterval = wx.StaticText( sbSizerPump.GetStaticBox(), wx.ID_ANY, u"Pump interval:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtPumpInterval.Wrap( -1 )
		self.m_txtPumpInterval.SetToolTipString( u"The time between the pump pulses" )
		
		gSizerPump.Add( self.m_txtPumpInterval, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		self.m_tcPumpInterval = wx.TextCtrl( sbSizerPump.GetStaticBox(), wx.ID_ANY, u"5000", wx.DefaultPosition, wx.Size( 60,-1 ), 0 )
		self.m_tcPumpInterval.SetToolTipString( u"The time between the pump pulses" )
		self.m_tcPumpInterval.SetMaxSize( wx.Size( 100,100 ) )
		
		gSizerPump.Add( self.m_tcPumpInterval, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, 5 )
		
		self.m_txtPumpIntervalUnit = wx.StaticText( sbSizerPump.GetStaticBox(), wx.ID_ANY, u"ms", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtPumpIntervalUnit.Wrap( -1 )
		gSizerPump.Add( self.m_txtPumpIntervalUnit, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		self.m_btnSetPumpInterval = wx.Button( sbSizerPump.GetStaticBox(), wx.ID_ANY, u"set", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_btnSetPumpInterval.SetToolTipString( u"Set the pump interval" )
		
		gSizerPump.Add( self.m_btnSetPumpInterval, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		self.m_txtPumpDuration = wx.StaticText( sbSizerPump.GetStaticBox(), wx.ID_ANY, u"Pump duration:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtPumpDuration.Wrap( -1 )
		self.m_txtPumpDuration.SetToolTipString( u"The duration of a pump puls" )
		
		gSizerPump.Add( self.m_txtPumpDuration, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		self.m_tcPumpDuration = wx.TextCtrl( sbSizerPump.GetStaticBox(), wx.ID_ANY, u"100", wx.DefaultPosition, wx.Size( 60,-1 ), 0 )
		self.m_tcPumpDuration.SetToolTipString( u"The duration of a pump puls" )
		
		gSizerPump.Add( self.m_tcPumpDuration, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, 5 )
		
		self.m_txtPumpDurationUnit = wx.StaticText( sbSizerPump.GetStaticBox(), wx.ID_ANY, u"ms", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtPumpDurationUnit.Wrap( -1 )
		gSizerPump.Add( self.m_txtPumpDurationUnit, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		self.m_btnSetPumpDuration = wx.Button( sbSizerPump.GetStaticBox(), wx.ID_ANY, u"set", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_btnSetPumpDuration.SetToolTipString( u"Set the pump duration" )
		
		gSizerPump.Add( self.m_btnSetPumpDuration, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		self.m_txtPumpPower = wx.StaticText( sbSizerPump.GetStaticBox(), wx.ID_ANY, u"Pump power:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtPumpPower.Wrap( -1 )
		gSizerPump.Add( self.m_txtPumpPower, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		self.m_sldPumpPower = wx.Slider( sbSizerPump.GetStaticBox(), wx.ID_ANY, 255, 0, 255, wx.DefaultPosition, wx.DefaultSize, wx.SL_HORIZONTAL )
		self.m_sldPumpPower.SetToolTipString( u"A value of over 90% is recommended with the standard pump" )
		
		gSizerPump.Add( self.m_sldPumpPower, 0, wx.ALL|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		self.m_txtPumpPowerPercentage = wx.StaticText( sbSizerPump.GetStaticBox(), wx.ID_ANY, u"100.0%", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtPumpPowerPercentage.Wrap( -1 )
		gSizerPump.Add( self.m_txtPumpPowerPercentage, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		self.m_btnSetPumpPower = wx.Button( sbSizerPump.GetStaticBox(), wx.ID_ANY, u"set", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_btnSetPumpPower.SetToolTipString( u"Set the pump power" )
		
		gSizerPump.Add( self.m_btnSetPumpPower, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		self.m_txtAirpumpPower = wx.StaticText( sbSizerPump.GetStaticBox(), wx.ID_ANY, u"Air pump power:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtAirpumpPower.Wrap( -1 )
		gSizerPump.Add( self.m_txtAirpumpPower, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		self.m_sldAirpumpPower = wx.Slider( sbSizerPump.GetStaticBox(), wx.ID_ANY, 255, 0, 255, wx.DefaultPosition, wx.DefaultSize, wx.SL_HORIZONTAL )
		self.m_sldAirpumpPower.SetToolTipString( u"A value of over 90% is recommended with the standard pump" )
		
		gSizerPump.Add( self.m_sldAirpumpPower, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, 5 )
		
		self.m_txtAirpumpPowerPercentage = wx.StaticText( sbSizerPump.GetStaticBox(), wx.ID_ANY, u"100.0%", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtAirpumpPowerPercentage.Wrap( -1 )
		gSizerPump.Add( self.m_txtAirpumpPowerPercentage, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		self.m_btnSetAirpumpPower = wx.Button( sbSizerPump.GetStaticBox(), wx.ID_ANY, u"set", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_btnSetAirpumpPower.SetToolTipString( u"Set the pump power" )
		
		gSizerPump.Add( self.m_btnSetAirpumpPower, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		
		sbSizerPump.Add( gSizerPump, 1, wx.EXPAND, 5 )
		
		
		fgSizerSuper.Add( sbSizerPump, 1, wx.EXPAND, 5 )
		
		sbSizerStirrer = wx.StaticBoxSizer( wx.StaticBox( self.m_pnlSettings, wx.ID_ANY, u"Stirrer" ), wx.VERTICAL )
		
		fgSizerStirrer = wx.FlexGridSizer( 2, 4, 0, 0 )
		fgSizerStirrer.SetFlexibleDirection( wx.BOTH )
		fgSizerStirrer.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )
		
		self.m_txtStirrerTargetSpeed = wx.StaticText( sbSizerStirrer.GetStaticBox(), wx.ID_ANY, u"Stirrer target speed:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtStirrerTargetSpeed.Wrap( -1 )
		fgSizerStirrer.Add( self.m_txtStirrerTargetSpeed, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		self.m_tcStirrerTargetSpeed = wx.TextCtrl( sbSizerStirrer.GetStaticBox(), wx.ID_ANY, u"800", wx.DefaultPosition, wx.Size( 60,-1 ), 0 )
		self.m_tcStirrerTargetSpeed.SetToolTipString( u"Stirrer target speed in rounds per minute" )
		
		fgSizerStirrer.Add( self.m_tcStirrerTargetSpeed, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, 5 )
		
		self.m_txtStirrerTargetSpeedUnit = wx.StaticText( sbSizerStirrer.GetStaticBox(), wx.ID_ANY, u"rpm", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtStirrerTargetSpeedUnit.Wrap( -1 )
		fgSizerStirrer.Add( self.m_txtStirrerTargetSpeedUnit, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5 )
		
		self.m_btnSetStirrerTargetSpeed = wx.Button( sbSizerStirrer.GetStaticBox(), wx.ID_ANY, u"set", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_btnSetStirrerTargetSpeed.SetToolTipString( u"Set the speed of the stirrer" )
		
		fgSizerStirrer.Add( self.m_btnSetStirrerTargetSpeed, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		self.m_txtStirrerSpeedText = wx.StaticText( sbSizerStirrer.GetStaticBox(), wx.ID_ANY, u"Stirrer speed:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtStirrerSpeedText.Wrap( -1 )
		fgSizerStirrer.Add( self.m_txtStirrerSpeedText, 0, wx.ALL, 5 )
		
		self.m_txtStirrerSpeed = wx.StaticText( sbSizerStirrer.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtStirrerSpeed.Wrap( -1 )
		self.m_txtStirrerSpeed.SetToolTipString( u"Stirrer speed in rounds per minute" )
		
		fgSizerStirrer.Add( self.m_txtStirrerSpeed, 0, wx.ALL, 5 )
		
		self.m_txtStirrerSpeedUnit = wx.StaticText( sbSizerStirrer.GetStaticBox(), wx.ID_ANY, u"rpm", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_txtStirrerSpeedUnit.Wrap( -1 )
		fgSizerStirrer.Add( self.m_txtStirrerSpeedUnit, 0, wx.ALL, 5 )
		
		
		fgSizerStirrer.AddSpacer( ( 0, 0), 1, wx.EXPAND, 5 )
		
		
		sbSizerStirrer.Add( fgSizerStirrer, 1, wx.EXPAND, 5 )
		
		
		fgSizerSuper.Add( sbSizerStirrer, 1, wx.EXPAND, 5 )
		
		
		self.m_pnlSettings.SetSizer( fgSizerSuper )
		self.m_pnlSettings.Layout()
		fgSizerSuper.Fit( self.m_pnlSettings )
		self.m_notebook.AddPage( self.m_pnlSettings, u"Settings", True )
		self.m_pnlGraphs = wx.Panel( self.m_notebook, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
		self.m_pnlGraphs.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_MENU ) )
		
		self.m_notebook.AddPage( self.m_pnlGraphs, u"Graphs", False )
		
		bSizer2.Add( self.m_notebook, 1, wx.EXPAND |wx.ALL, 5 )
		
		
		self.SetSizer( bSizer2 )
		self.Layout()
		
		# Connect Events
		self.Bind( wx.EVT_CLOSE, self.OnClose )
		self.m_btnConnect.Bind( wx.EVT_BUTTON, self.OnConnect )
		self.m_btnSetI0.Bind( wx.EVT_BUTTON, self.OnSetI0 )
		self.m_btnSetTargetOD.Bind( wx.EVT_BUTTON, self.OnSetTargetOD )
		self.m_rbPumpMode.Bind( wx.EVT_RADIOBOX, self.OnSelectPumpMode )
		self.m_tbManualPump.Bind( wx.EVT_TOGGLEBUTTON, self.OnManualPump )
		self.m_btnSetPumpInterval.Bind( wx.EVT_BUTTON, self.OnSetPumpInterval )
		self.m_btnSetPumpDuration.Bind( wx.EVT_BUTTON, self.OnSetPumpDuration )
		self.m_sldPumpPower.Bind( wx.EVT_SCROLL, self.OnPumpPowerSlider )
		self.m_btnSetPumpPower.Bind( wx.EVT_BUTTON, self.OnSetPumpPower )
		self.m_sldAirpumpPower.Bind( wx.EVT_SCROLL, self.OnAirpumpPowerSlider )
		self.m_btnSetAirpumpPower.Bind( wx.EVT_BUTTON, self.OnSetAirpumpPower )
		self.m_btnSetStirrerTargetSpeed.Bind( wx.EVT_BUTTON, self.OnSetStirrerTargetSpeed )
	
	def __del__( self ):
		pass
	
	
	# Virtual event handlers, overide them in your derived class
	def OnClose( self, event ):
		event.Skip()
	
	def OnConnect( self, event ):
		event.Skip()
	
	def OnSetI0( self, event ):
		event.Skip()
	
	def OnSetTargetOD( self, event ):
		event.Skip()
	
	def OnSelectPumpMode( self, event ):
		event.Skip()
	
	def OnManualPump( self, event ):
		event.Skip()
	
	def OnSetPumpInterval( self, event ):
		event.Skip()
	
	def OnSetPumpDuration( self, event ):
		event.Skip()
	
	def OnPumpPowerSlider( self, event ):
		event.Skip()
	
	def OnSetPumpPower( self, event ):
		event.Skip()
	
	def OnAirpumpPowerSlider( self, event ):
		event.Skip()
	
	def OnSetAirpumpPower( self, event ):
		event.Skip()
	
	def OnSetStirrerTargetSpeed( self, event ):
		event.Skip()
	

