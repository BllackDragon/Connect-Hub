#Requires -Version 5.0
<#
.SYNOPSIS
    VPN + VNC Launcher — WPF, dark modern UI.
#>
[CmdletBinding()]
param([string]$ConfigPath = '')

if (-not $ConfigPath) {
    $scriptDir = if ($PSScriptRoot) { $PSScriptRoot }
                 elseif ($MyInvocation.MyCommand.Path) { Split-Path -Parent $MyInvocation.MyCommand.Path }
                 else { (Get-Location).Path }
    $ConfigPath = Join-Path $scriptDir 'launcher_config.json'
}

Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName WindowsBase
Add-Type -AssemblyName System.Xaml
Add-Type -AssemblyName System.Windows.Forms

# ============================================================
#                     CONFIG
# ============================================================
$defaultConfig = [ordered]@{
    vpn_dir              = 'X:\openvpn\start'
    vnc_root             = 'M:\Обмен HRC СО\VNC'
    vpn_timeout          = 60
    vpn_soft_up_after    = 15
    vnc_extensions       = @('.vnc', '.lnk', '.rdp', '.bat')
    vnc_exclude_patterns = @('неактивн', 'устаревш')
    extra_vnc_roots      = @()
}
if (-not (Test-Path -LiteralPath $ConfigPath)) {
    ($defaultConfig | ConvertTo-Json -Depth 5) |
        Set-Content -LiteralPath $ConfigPath -Encoding UTF8
}
$cfg = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($k in $defaultConfig.Keys) {
    if ($null -eq $cfg.$k) { $cfg | Add-Member -NotePropertyName $k -NotePropertyValue $defaultConfig[$k] -Force }
}

$script:vncExts  = @($cfg.vnc_extensions | ForEach-Object { $_.ToString().ToLower() })
$script:excludes = @($cfg.vnc_exclude_patterns | ForEach-Object { $_.ToString().ToLower() })
$script:vpnList  = @()
$script:allFiles = @()
$script:sessions = [System.Collections.ArrayList]::new()
$script:sessionId = 0
$script:activeSessionId = 0

# ============================================================
#                         XAML
# ============================================================
[xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="VPN + VNC Launcher"
        Width="1340" Height="900"
        MinWidth="1100" MinHeight="700"
        Background="#0d1117"
        WindowStartupLocation="CenterScreen"
        FontFamily="Segoe UI"
        UseLayoutRounding="True"
        TextOptions.TextFormattingMode="Ideal"
        TextOptions.TextRenderingMode="ClearType">

  <Window.Resources>
    <!-- ============ BRUSHES ============ -->
    <SolidColorBrush x:Key="BgBrush"        Color="#0d1117"/>
    <SolidColorBrush x:Key="CardBrush"      Color="#161b22"/>
    <SolidColorBrush x:Key="Card2Brush"     Color="#21262d"/>
    <SolidColorBrush x:Key="BorderBrush"    Color="#30363d"/>
    <SolidColorBrush x:Key="BorderHover"    Color="#484f58"/>
    <SolidColorBrush x:Key="TextBrush"      Color="#c9d1d9"/>
    <SolidColorBrush x:Key="TextMuted"      Color="#8b949e"/>
    <SolidColorBrush x:Key="TextDim"        Color="#6e7681"/>
    <SolidColorBrush x:Key="BlueBrush"      Color="#58a6ff"/>
    <SolidColorBrush x:Key="BlueBtn"        Color="#1f6feb"/>
    <SolidColorBrush x:Key="BlueBtnHover"   Color="#388bfd"/>
    <SolidColorBrush x:Key="GreenBrush"     Color="#3fb950"/>
    <SolidColorBrush x:Key="RedBrush"       Color="#f85149"/>
    <SolidColorBrush x:Key="RedBtn"         Color="#da3633"/>
    <SolidColorBrush x:Key="RedBtnHover"    Color="#f85149"/>
    <SolidColorBrush x:Key="AmberBrush"     Color="#d29922"/>
    <SolidColorBrush x:Key="TermBg"         Color="#010409"/>

    <!-- ============ SCROLLBAR ============ -->
    <Style TargetType="ScrollBar">
      <Setter Property="Background" Value="Transparent"/>
      <Setter Property="Width" Value="10"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="ScrollBar">
            <Grid Background="Transparent">
              <Track x:Name="PART_Track" IsDirectionReversed="True">
                <Track.DecreaseRepeatButton>
                  <RepeatButton Command="ScrollBar.PageUpCommand" Opacity="0" Focusable="False"/>
                </Track.DecreaseRepeatButton>
                <Track.Thumb>
                  <Thumb>
                    <Thumb.Template>
                      <ControlTemplate TargetType="Thumb">
                        <Border Background="#30363d" CornerRadius="5" Margin="2,0"/>
                      </ControlTemplate>
                    </Thumb.Template>
                  </Thumb>
                </Track.Thumb>
                <Track.IncreaseRepeatButton>
                  <RepeatButton Command="ScrollBar.PageDownCommand" Opacity="0" Focusable="False"/>
                </Track.IncreaseRepeatButton>
              </Track>
            </Grid>
            <ControlTemplate.Triggers>
              <Trigger Property="Orientation" Value="Horizontal">
                <Setter Property="Height" Value="10"/>
                <Setter Property="Width" Value="Auto"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <!-- ============ BUTTON: PRIMARY ============ -->
    <Style x:Key="PrimaryBtn" TargetType="Button">
      <Setter Property="Background" Value="{StaticResource BlueBtn}"/>
      <Setter Property="Foreground" Value="White"/>
      <Setter Property="BorderThickness" Value="0"/>
      <Setter Property="Padding" Value="16,7"/>
      <Setter Property="FontSize" Value="12"/>
      <Setter Property="FontWeight" Value="SemiBold"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border x:Name="Bd" Background="{TemplateBinding Background}" CornerRadius="6"
                    Padding="{TemplateBinding Padding}">
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="Bd" Property="Background" Value="{StaticResource BlueBtnHover}"/>
              </Trigger>
              <Trigger Property="IsEnabled" Value="False">
                <Setter TargetName="Bd" Property="Opacity" Value="0.4"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <!-- ============ BUTTON: GHOST ============ -->
    <Style x:Key="GhostBtn" TargetType="Button">
      <Setter Property="Background" Value="Transparent"/>
      <Setter Property="Foreground" Value="{StaticResource TextBrush}"/>
      <Setter Property="BorderBrush" Value="{StaticResource BorderBrush}"/>
      <Setter Property="BorderThickness" Value="1"/>
      <Setter Property="Padding" Value="16,7"/>
      <Setter Property="FontSize" Value="12"/>
      <Setter Property="FontWeight" Value="SemiBold"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border x:Name="Bd" Background="{TemplateBinding Background}"
                    BorderBrush="{TemplateBinding BorderBrush}"
                    BorderThickness="{TemplateBinding BorderThickness}"
                    CornerRadius="6"
                    Padding="{TemplateBinding Padding}">
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="Bd" Property="Background" Value="{StaticResource Card2Brush}"/>
                <Setter TargetName="Bd" Property="BorderBrush" Value="{StaticResource BorderHover}"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <!-- ============ BUTTON: DANGER ============ -->
    <Style x:Key="DangerBtn" TargetType="Button">
      <Setter Property="Background" Value="{StaticResource RedBtn}"/>
      <Setter Property="Foreground" Value="White"/>
      <Setter Property="BorderThickness" Value="0"/>
      <Setter Property="Padding" Value="16,7"/>
      <Setter Property="FontSize" Value="12"/>
      <Setter Property="FontWeight" Value="SemiBold"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border x:Name="Bd" Background="{TemplateBinding Background}" CornerRadius="6"
                    Padding="{TemplateBinding Padding}">
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="Bd" Property="Background" Value="{StaticResource RedBtnHover}"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <!-- ============ TEXTBOX: SEARCH ============ -->
    <Style x:Key="SearchBox" TargetType="TextBox">
      <Setter Property="Background" Value="#0d1117"/>
      <Setter Property="Foreground" Value="{StaticResource TextBrush}"/>
      <Setter Property="BorderBrush" Value="{StaticResource BorderBrush}"/>
      <Setter Property="BorderThickness" Value="1"/>
      <Setter Property="Padding" Value="10,7"/>
      <Setter Property="FontSize" Value="12"/>
      <Setter Property="CaretBrush" Value="{StaticResource BlueBrush}"/>
      <Setter Property="SelectionBrush" Value="{StaticResource BlueBrush}"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="TextBox">
            <Border x:Name="Bd" Background="{TemplateBinding Background}"
                    BorderBrush="{TemplateBinding BorderBrush}"
                    BorderThickness="{TemplateBinding BorderThickness}"
                    CornerRadius="6">
              <ScrollViewer x:Name="PART_ContentHost" Margin="{TemplateBinding Padding}"
                            VerticalAlignment="Center"/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsFocused" Value="True">
                <Setter TargetName="Bd" Property="BorderBrush" Value="{StaticResource BlueBrush}"/>
              </Trigger>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="Bd" Property="BorderBrush" Value="{StaticResource BorderHover}"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <!-- ============ LISTBOX: VPN ============ -->
    <Style x:Key="VpnList" TargetType="ListBox">
      <Setter Property="Background" Value="Transparent"/>
      <Setter Property="BorderThickness" Value="0"/>
      <Setter Property="ScrollViewer.HorizontalScrollBarVisibility" Value="Disabled"/>
      <Setter Property="ScrollViewer.VerticalScrollBarVisibility" Value="Auto"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="ListBox">
            <ScrollViewer Focusable="False" Padding="{TemplateBinding Padding}">
              <ItemsPresenter/>
            </ScrollViewer>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <Style x:Key="VpnItem" TargetType="ListBoxItem">
      <Setter Property="Foreground" Value="{StaticResource TextBrush}"/>
      <Setter Property="Padding" Value="0"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="ListBoxItem">
            <Border x:Name="Bd" Background="Transparent" CornerRadius="6"
                    Padding="10,7" Margin="0,1">
              <ContentPresenter/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="Bd" Property="Background" Value="{StaticResource Card2Brush}"/>
              </Trigger>
              <Trigger Property="IsSelected" Value="True">
                <Setter TargetName="Bd" Property="Background" Value="#1f6feb"/>
                <Setter Property="Foreground" Value="White"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <!-- ============ TREEVIEW ============ -->
    <Style x:Key="TreeViewDark" TargetType="TreeView">
      <Setter Property="Background" Value="Transparent"/>
      <Setter Property="BorderThickness" Value="0"/>
      <Setter Property="Foreground" Value="{StaticResource TextBrush}"/>
      <Setter Property="ScrollViewer.HorizontalScrollBarVisibility" Value="Auto"/>
    </Style>

    <Style x:Key="TreeItem" TargetType="TreeViewItem">
      <Setter Property="Foreground" Value="{StaticResource TextBrush}"/>
      <Setter Property="IsExpanded" Value="False"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="TreeViewItem">
            <StackPanel>
              <Border x:Name="Bd" Background="Transparent" CornerRadius="4"
                      Padding="4,3" Margin="0,1">
                <Grid>
                  <Grid.ColumnDefinitions>
                    <ColumnDefinition Width="Auto"/>
                    <ColumnDefinition Width="*"/>
                  </Grid.ColumnDefinitions>
                  <ToggleButton x:Name="Expander" ClickMode="Press"
                                IsChecked="{Binding IsExpanded, RelativeSource={RelativeSource TemplatedParent}}"
                                Background="Transparent" BorderThickness="0"
                                Foreground="{StaticResource TextMuted}"
                                Width="14" Height="14" Focusable="False">
                    <ToggleButton.Template>
                      <ControlTemplate TargetType="ToggleButton">
                        <Border Background="Transparent" Width="14" Height="14">
                          <TextBlock x:Name="Arrow" Text="&#xE76C;"
                                     FontFamily="Segoe MDL2 Assets" FontSize="8"
                                     HorizontalAlignment="Center" VerticalAlignment="Center"
                                     Foreground="{StaticResource TextMuted}"/>
                        </Border>
                        <ControlTemplate.Triggers>
                          <Trigger Property="IsChecked" Value="True">
                            <Setter TargetName="Arrow" Property="Text" Value="&#xE70D;"/>
                          </Trigger>
                          <Trigger Property="IsMouseOver" Value="True">
                            <Setter TargetName="Arrow" Property="Foreground" Value="{StaticResource TextBrush}"/>
                          </Trigger>
                        </ControlTemplate.Triggers>
                      </ControlTemplate>
                    </ToggleButton.Template>
                  </ToggleButton>
                  <ContentPresenter Grid.Column="1" ContentSource="Header" Margin="4,0,0,0"/>
                </Grid>
              </Border>
              <ItemsPresenter x:Name="ItemsHost" Margin="16,0,0,0"/>
            </StackPanel>
            <ControlTemplate.Triggers>
              <Trigger Property="IsExpanded" Value="False">
                <Setter TargetName="ItemsHost" Property="Visibility" Value="Collapsed"/>
              </Trigger>
              <Trigger Property="HasItems" Value="False">
                <Setter TargetName="Expander" Property="Visibility" Value="Hidden"/>
              </Trigger>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="Bd" Property="Background" Value="{StaticResource Card2Brush}"/>
              </Trigger>
              <Trigger Property="IsSelected" Value="True">
                <Setter TargetName="Bd" Property="Background" Value="#1f6feb"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <!-- ============ TAB BUTTON ============ -->
    <Style x:Key="TabBtn" TargetType="Button">
      <Setter Property="Foreground" Value="{StaticResource TextMuted}"/>
      <Setter Property="Background" Value="Transparent"/>
      <Setter Property="BorderThickness" Value="0"/>
      <Setter Property="Padding" Value="12,0"/>
      <Setter Property="FontSize" Value="12"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border x:Name="Bd" Background="{TemplateBinding Background}"
                    CornerRadius="6" Padding="{TemplateBinding Padding}" Margin="2,0">
              <ContentPresenter VerticalAlignment="Center"/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="Bd" Property="Background" Value="{StaticResource Card2Brush}"/>
                <Setter Property="Foreground" Value="{StaticResource TextBrush}"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <!-- ============ PILL ============ -->
    <Style x:Key="Pill" TargetType="Border">
      <Setter Property="CornerRadius" Value="12"/>
      <Setter Property="Padding" Value="10,4"/>
      <Setter Property="Margin" Value="0,0,8,0"/>
    </Style>

  </Window.Resources>

  <Grid>
    <Grid.RowDefinitions>
      <RowDefinition Height="Auto"/>
      <RowDefinition Height="*"/>
      <RowDefinition Height="300"/>
      <RowDefinition Height="Auto"/>
    </Grid.RowDefinitions>

    <!-- ==================== HEADER ==================== -->
    <Border Grid.Row="0" Background="{StaticResource CardBrush}"
            BorderBrush="{StaticResource BorderBrush}" BorderThickness="0,0,0,1"
            Padding="20,14">
      <Grid>
        <Grid.ColumnDefinitions>
          <ColumnDefinition Width="Auto"/>
          <ColumnDefinition Width="*"/>
          <ColumnDefinition Width="Auto"/>
        </Grid.ColumnDefinitions>

        <StackPanel Grid.Column="0" Orientation="Horizontal" VerticalAlignment="Center">
          <TextBlock Text="&#xE7EF;" FontFamily="Segoe MDL2 Assets" FontSize="18"
                     Foreground="{StaticResource BlueBrush}" VerticalAlignment="Center"/>
          <TextBlock Text="VPN + VNC Launcher" FontSize="16" FontWeight="SemiBold"
                     Foreground="{StaticResource TextBrush}" Margin="10,0,0,0" VerticalAlignment="Center"/>
        </StackPanel>

        <StackPanel Grid.Column="1" Orientation="Horizontal" HorizontalAlignment="Left"
                    Margin="40,0,0,0" VerticalAlignment="Center">
          <Border Style="{StaticResource Pill}" Background="#0c2d48">
            <StackPanel Orientation="Horizontal">
              <Ellipse Width="8" Height="8" Fill="{StaticResource BlueBrush}" VerticalAlignment="Center"/>
              <TextBlock x:Name="PillVpn" Text="0 профилей" Margin="7,0,0,0"
                         Foreground="{StaticResource TextBrush}" FontSize="11" VerticalAlignment="Center"/>
            </StackPanel>
          </Border>
          <Border Style="{StaticResource Pill}" Background="#3d2a05">
            <StackPanel Orientation="Horizontal">
              <Ellipse Width="8" Height="8" Fill="{StaticResource AmberBrush}" VerticalAlignment="Center"/>
              <TextBlock x:Name="PillActive" Text="0 активных" Margin="7,0,0,0"
                         Foreground="{StaticResource TextBrush}" FontSize="11" VerticalAlignment="Center"/>
            </StackPanel>
          </Border>
          <Border Style="{StaticResource Pill}" Background="#0d2f1b">
            <StackPanel Orientation="Horizontal">
              <Ellipse Width="8" Height="8" Fill="{StaticResource GreenBrush}" VerticalAlignment="Center"/>
              <TextBlock x:Name="PillFiles" Text="0 файлов" Margin="7,0,0,0"
                         Foreground="{StaticResource TextBrush}" FontSize="11" VerticalAlignment="Center"/>
            </StackPanel>
          </Border>
        </StackPanel>

        <StackPanel Grid.Column="2" Orientation="Horizontal" VerticalAlignment="Center">
          <Button x:Name="BtnRefresh" Content="ОБНОВИТЬ" Style="{StaticResource GhostBtn}"
                  Margin="0,0,8,0" Height="32"/>
          <Button x:Name="BtnDisconnectAll" Content="ОТКЛЮЧИТЬ ВСЁ"
                  Style="{StaticResource DangerBtn}" Height="32"/>
        </StackPanel>
      </Grid>
    </Border>

    <!-- ==================== MAIN ==================== -->
    <Grid Grid.Row="1" Margin="16,14,16,8">
      <Grid.ColumnDefinitions>
        <ColumnDefinition Width="400"/>
        <ColumnDefinition Width="*"/>
      </Grid.ColumnDefinitions>

      <!-- LEFT: VPN profiles -->
      <Border Grid.Column="0" Background="{StaticResource CardBrush}"
              BorderBrush="{StaticResource BorderBrush}" BorderThickness="1"
              CornerRadius="10" Margin="0,0,7,0">
        <Grid>
          <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="*"/>
          </Grid.RowDefinitions>

          <Grid Grid.Row="0" Margin="16,14,16,8">
            <StackPanel Orientation="Horizontal">
              <TextBlock Text="VPN ПРОФИЛИ" FontSize="11" FontWeight="SemiBold"
                         Foreground="{StaticResource TextMuted}"/>
              <Border Background="#21262d" CornerRadius="10" Padding="7,2" Margin="8,0,0,0">
                <TextBlock x:Name="BadgeVpn" Text="0" FontSize="10"
                           Foreground="{StaticResource TextMuted}"/>
              </Border>
            </StackPanel>
          </Grid>

          <Grid Grid.Row="1" Margin="16,0,16,10">
            <TextBox x:Name="TxtVpnSearch" Style="{StaticResource SearchBox}" Height="32"/>
            <TextBlock Text="Поиск по имени..."
                       Foreground="{StaticResource TextDim}" FontSize="12"
                       Margin="11,0,0,0" VerticalAlignment="Center" IsHitTestVisible="False">
              <TextBlock.Style>
                <Style TargetType="TextBlock">
                  <Setter Property="Visibility" Value="Collapsed"/>
                  <Style.Triggers>
                    <DataTrigger Binding="{Binding Text, ElementName=TxtVpnSearch}" Value="">
                      <Setter Property="Visibility" Value="Visible"/>
                    </DataTrigger>
                  </Style.Triggers>
                </Style>
              </TextBlock.Style>
            </TextBlock>
          </Grid>

          <ListBox Grid.Row="2" x:Name="LstVpn" Style="{StaticResource VpnList}"
                   ItemContainerStyle="{StaticResource VpnItem}"
                   Margin="8,0,8,10" Padding="4"/>
        </Grid>
      </Border>

      <!-- RIGHT: VNC files -->
      <Border Grid.Column="1" Background="{StaticResource CardBrush}"
              BorderBrush="{StaticResource BorderBrush}" BorderThickness="1"
              CornerRadius="10" Margin="7,0,0,0">
        <Grid>
          <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="*"/>
            <RowDefinition Height="Auto"/>
          </Grid.RowDefinitions>

          <Grid Grid.Row="0" Margin="16,14,16,8">
            <StackPanel Orientation="Horizontal">
              <TextBlock Text="ФАЙЛЫ ПОДКЛЮЧЕНИЯ" FontSize="11" FontWeight="SemiBold"
                         Foreground="{StaticResource TextMuted}"/>
              <Border Background="#21262d" CornerRadius="10" Padding="7,2" Margin="8,0,0,0">
                <TextBlock x:Name="BadgeFiles" Text="0" FontSize="10"
                           Foreground="{StaticResource TextMuted}"/>
              </Border>
            </StackPanel>
          </Grid>

          <Grid Grid.Row="1" Margin="16,0,16,10">
            <TextBox x:Name="TxtSearch" Style="{StaticResource SearchBox}" Height="32"/>
            <TextBlock Text="Поиск по имени или пути..."
                       Foreground="{StaticResource TextDim}" FontSize="12"
                       Margin="11,0,0,0" VerticalAlignment="Center" IsHitTestVisible="False">
              <TextBlock.Style>
                <Style TargetType="TextBlock">
                  <Setter Property="Visibility" Value="Collapsed"/>
                  <Style.Triggers>
                    <DataTrigger Binding="{Binding Text, ElementName=TxtSearch}" Value="">
                      <Setter Property="Visibility" Value="Visible"/>
                    </DataTrigger>
                  </Style.Triggers>
                </Style>
              </TextBlock.Style>
            </TextBlock>
          </Grid>

          <TreeView Grid.Row="2" x:Name="TreeVnc" Style="{StaticResource TreeViewDark}"
                    ItemContainerStyle="{StaticResource TreeItem}"
                    Margin="8,0,8,8" Padding="4"/>

          <StackPanel Grid.Row="3" Orientation="Horizontal" Margin="16,0,16,14">
            <Button x:Name="BtnOpenFile" Content="ОТКРЫТЬ"
                    Style="{StaticResource PrimaryBtn}" Height="32" Margin="0,0,8,0"/>
            <Button x:Name="BtnShowInFolder" Content="ПОКАЗАТЬ В ПАПКЕ"
                    Style="{StaticResource GhostBtn}" Height="32"/>
          </StackPanel>
        </Grid>
      </Border>
    </Grid>

    <!-- ==================== SESSIONS ==================== -->
    <Border Grid.Row="2" Background="{StaticResource CardBrush}"
            BorderBrush="{StaticResource BorderBrush}" BorderThickness="1"
            CornerRadius="10" Margin="16,0,16,8">
      <Grid>
        <Grid.RowDefinitions>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="*"/>
        </Grid.RowDefinitions>

        <Grid Grid.Row="0" Margin="16,12,16,6">
          <StackPanel Orientation="Horizontal">
            <TextBlock Text="АКТИВНЫЕ СЕССИИ" FontSize="11" FontWeight="SemiBold"
                       Foreground="{StaticResource TextMuted}"/>
            <Border Background="#21262d" CornerRadius="10" Padding="7,2" Margin="8,0,0,0">
              <TextBlock x:Name="BadgeSessions" Text="0" FontSize="10"
                         Foreground="{StaticResource TextMuted}"/>
            </Border>
          </StackPanel>
        </Grid>

        <Border Grid.Row="1" Background="#0d1117" CornerRadius="6" Margin="16,0,16,8"
                Padding="4" MinHeight="36">
          <ScrollViewer HorizontalScrollBarVisibility="Auto"
                        VerticalScrollBarVisibility="Disabled">
            <StackPanel x:Name="TabPanel" Orientation="Horizontal"/>
          </ScrollViewer>
        </Border>

        <Border Grid.Row="2" Background="{StaticResource TermBg}" CornerRadius="6"
                Margin="16,0,16,14">
          <Grid x:Name="SessionHost"/>
        </Border>
      </Grid>
    </Border>

    <!-- ==================== STATUS BAR ==================== -->
    <Border Grid.Row="3" Background="{StaticResource CardBrush}"
            BorderBrush="{StaticResource BorderBrush}" BorderThickness="0,1,0,0"
            Padding="20,6">
      <Grid>
        <TextBlock x:Name="StatusLeft" Text="Готов."
                   Foreground="{StaticResource TextMuted}" FontSize="11"/>
        <TextBlock x:Name="StatusRight" Text=""
                   HorizontalAlignment="Right"
                   Foreground="{StaticResource TextMuted}" FontSize="11"/>
      </Grid>
    </Border>
  </Grid>
</Window>
"@

$reader = New-Object System.Xml.XmlNodeReader $xaml
$win = [Windows.Markup.XamlReader]::Load($reader)

# Ссылки на элементы
$PillVpn         = $win.FindName('PillVpn')
$PillActive      = $win.FindName('PillActive')
$PillFiles       = $win.FindName('PillFiles')
$BtnRefresh      = $win.FindName('BtnRefresh')
$BtnDisconnectAll= $win.FindName('BtnDisconnectAll')
$BadgeVpn        = $win.FindName('BadgeVpn')
$BadgeFiles      = $win.FindName('BadgeFiles')
$BadgeSessions   = $win.FindName('BadgeSessions')
$TxtVpnSearch    = $win.FindName('TxtVpnSearch')
$TxtSearch       = $win.FindName('TxtSearch')
$LstVpn          = $win.FindName('LstVpn')
$TreeVnc         = $win.FindName('TreeVnc')
$BtnOpenFile     = $win.FindName('BtnOpenFile')
$BtnShowInFolder = $win.FindName('BtnShowInFolder')
$TabPanel        = $win.FindName('TabPanel')
$SessionHost     = $win.FindName('SessionHost')
$StatusLeft      = $win.FindName('StatusLeft')
$StatusRight     = $win.FindName('StatusRight')

# ============================================================
#             КИСТИ И ЦВЕТА ДЛЯ КОДА
# ============================================================
$brBg     = [Windows.Media.BrushConverter]::new().ConvertFromString('#161b22')
$brBg2    = [Windows.Media.BrushConverter]::new().ConvertFromString('#21262d')
$brText   = [Windows.Media.BrushConverter]::new().ConvertFromString('#c9d1d9')
$brMuted  = [Windows.Media.BrushConverter]::new().ConvertFromString('#8b949e')
$brDim    = [Windows.Media.BrushConverter]::new().ConvertFromString('#6e7681')
$brBlue   = [Windows.Media.BrushConverter]::new().ConvertFromString('#58a6ff')
$brBlueBtn= [Windows.Media.BrushConverter]::new().ConvertFromString('#1f6feb')
$brBlueHov= [Windows.Media.BrushConverter]::new().ConvertFromString('#388bfd')
$brGreen  = [Windows.Media.BrushConverter]::new().ConvertFromString('#3fb950')
$brRed    = [Windows.Media.BrushConverter]::new().ConvertFromString('#f85149')
$brAmber  = [Windows.Media.BrushConverter]::new().ConvertFromString('#d29922')
$brTermFg = [Windows.Media.BrushConverter]::new().ConvertFromString('#c9d1d9')
$brTermCyan=[Windows.Media.BrushConverter]::new().ConvertFromString('#79c0ff')
$brTermGrn=[Windows.Media.BrushConverter]::new().ConvertFromString('#7ee787')

$script:brBlueBtn = $brBlueBtn

# ============================================================
#              БЫСТРЫЕ КОНСТРУКТОРЫ UI
# ============================================================
function New-Text([string]$t, [double]$size = 12, $brush = $null, [string]$weight = 'Normal') {
    $tb = New-Object Windows.Controls.TextBlock
    $tb.Text = $t; $tb.FontSize = $size
    if ($brush) { $tb.Foreground = $brush }
    try { $tb.FontWeight = [Windows.FontWeight]::new() } catch {}
    switch ($weight) {
        'SemiBold' { $tb.FontWeight = [Windows.FontWeights]::SemiBold }
        'Bold'     { $tb.FontWeight = [Windows.FontWeights]::Bold }
        default    { $tb.FontWeight = [Windows.FontWeights]::Normal }
    }
    $tb.VerticalAlignment = 'Center'
    return $tb
}

function New-IconText([string]$glyph, [double]$size = 14, $brush = $null) {
    $tb = New-Object Windows.Controls.TextBlock
    $tb.Text = $glyph
    $tb.FontFamily = New-Object Windows.Media.FontFamily('Segoe MDL2 Assets')
    $tb.FontSize = $size
    if ($brush) { $tb.Foreground = $brush }
    $tb.VerticalAlignment = 'Center'
    return $tb
}

# ============================================================
#              ФУНКЦИИ СКАНИРОВАНИЯ
# ============================================================
function Test-Excluded([string]$name) {
    $n = $name.ToLower()
    foreach ($p in $script:excludes) { if ($n -like "*$p*") { return $true } }
    return $false
}

function Scan-Vpn {
    $script:vpnList = @()
    if (-not (Test-Path -LiteralPath $cfg.vpn_dir)) { return }
    $script:vpnList = @(Get-ChildItem -LiteralPath $cfg.vpn_dir -Filter '*.bat' -File -ErrorAction SilentlyContinue |
                        Sort-Object Name)
}

function Scan-Vnc {
    $script:allFiles = @()
    $roots = @($cfg.vnc_root) + @($cfg.extra_vnc_roots)
    $extSet = [System.Collections.Generic.HashSet[string]]::new()
    foreach ($e in $script:vncExts) { [void]$extSet.Add($e) }

    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root)) { continue }
        $all = Get-ChildItem -LiteralPath $root -Recurse -File -Force -ErrorAction SilentlyContinue
        foreach ($f in $all) {
            if (-not $extSet.Contains($f.Extension.ToLower())) { continue }
            $skip = $false
            $p = $f.Directory
            while ($p -and $p.FullName.Length -gt $root.Length) {
                $n = $p.Name.ToLower()
                foreach ($pat in $script:excludes) { if ($n -like "*$pat*") { $skip = $true; break } }
                if ($skip) { break }
                $p = $p.Parent
            }
            if (-not $skip) { $script:allFiles += $f }
        }
    }
    $script:allFiles = @($script:allFiles | Sort-Object FullName)
}

# ============================================================
#              РЕНДЕР СПИСКА VPN (ListBox)
# ============================================================
function Render-VpnList {
    $LstVpn.Items.Clear()
    $q = $TxtVpnSearch.Text.Trim().ToLower()

    foreach ($f in $script:vpnList) {
        if ($q -and -not $f.BaseName.ToLower().Contains($q)) { continue }

        $sp = New-Object Windows.Controls.StackPanel
        $sp.Orientation = 'Horizontal'

        $icon = New-IconText ([char]0xE7C3) 14 $script:brGreen
        $icon.Margin = New-Object Windows.Thickness(0,0,10,0)
        [void]$sp.Children.Add($icon)

        $name = New-Text $f.BaseName 12 $brText
        $name.TextTrimming = 'CharacterEllipsis'
        [void]$sp.Children.Add($name)

        $item = New-Object Windows.Controls.ListBoxItem
        $item.Content = $sp
        $item.Tag = $f.FullName
        $item.HorizontalContentAlignment = 'Stretch'
        [void]$LstVpn.Items.Add($item)
    }
}

# ============================================================
#              РЕНДЕР ДЕРЕВА (TreeView)
# ============================================================
function Build-Tree {
    $TreeVnc.Items.Clear()
    $q = $TxtSearch.Text.Trim()
    $files = $script:allFiles
    if ($q) {
        $ql = $q.ToLower()
        $files = @($files | Where-Object {
            $_.Name.ToLower().Contains($ql) -or $_.FullName.ToLower().Contains($ql)
        })
    }

    $root = $cfg.vnc_root
    $rootNode = New-Object Windows.Controls.TreeViewItem
    $rootNode.Header = (New-TreeHeader $root ([char]0xE8B7) $brBlue)
    $rootNode.Tag = $root
    $rootNode.IsExpanded = $true

    $folders = @{ $root = $rootNode }
    $rootLen = $root.TrimEnd('\').Length

    foreach ($f in $files) {
        if (-not $f) { continue }
        $rel = $f.FullName.Substring($rootLen).TrimStart('\')
        $parts = $rel -split '\\'
        $parentPath = $root
        for ($i=0; $i -lt $parts.Count-1; $i++) {
            $folderPath = (Join-Path $parentPath $parts[$i])
            if (-not $folders.ContainsKey($folderPath)) {
                $node = New-Object Windows.Controls.TreeViewItem
                $node.Header = (New-TreeHeader $parts[$i] ([char]0xE8B7) $brAmber)
                $node.Tag = $folderPath
                [void]$folders[$parentPath].Items.Add($node)
                $folders[$folderPath] = $node
            }
            $parentPath = $folderPath
        }
        $isVnc = $script:vncExts -contains $f.Extension.ToLower()
        $fileNode = New-Object Windows.Controls.TreeViewItem
        $fileNode.Header = (New-TreeHeader $f.Name ([char]0xE7C3) $(if ($isVnc) { $brBlue } else { $brDim }))
        $fileNode.Tag = $f.FullName
        [void]$folders[$parentPath].Items.Add($fileNode)
    }
    [void]$TreeVnc.Items.Add($rootNode)
}

function New-TreeHeader([string]$text, [string]$glyph, $brush) {
    $sp = New-Object Windows.Controls.StackPanel
    $sp.Orientation = 'Horizontal'
    $icon = New-IconText $glyph 13 $brush
    $icon.Margin = New-Object Windows.Thickness(0,0,8,0)
    [void]$sp.Children.Add($icon)
    $tb = New-Text $text 12 $brText
    [void]$sp.Children.Add($tb)
    return $sp
}

# ============================================================
#              ОБНОВЛЕНИЕ СЧЁТЧИКОВ
# ============================================================
function Update-Counters {
    $activeCount = @($script:sessions | Where-Object { $_.Proc -and -not $_.Proc.HasExited }).Count
    $PillVpn.Text    = "$($script:vpnList.Count) профилей"
    $PillActive.Text = "$activeCount активных"
    $PillFiles.Text  = "$($script:allFiles.Count) файлов"
    $BadgeVpn.Text   = "$($script:vpnList.Count)"
    $BadgeFiles.Text = "$($script:allFiles.Count)"
    $BadgeSessions.Text = "$activeCount"
    $StatusLeft.Text = "Профилей: $($script:vpnList.Count)   ·   Файлов: $($script:allFiles.Count)   ·   Активных сессий: $activeCount"
}

# ============================================================
#              УПРАВЛЕНИЕ СЕССИЯМИ
# ============================================================
function New-Session([string]$BatPath) {
    $script:sessionId++
    $s = [pscustomobject]@{
        Id = $script:sessionId
        BatPath = $BatPath
        Name = [IO.Path]::GetFileNameWithoutExtension($BatPath)
        Proc = $null; LogFile = $null; RunnerPs = $null
        LogPos = 0; Ready = $false; SoftUp = $false
        StartTime = $null; Status = 'starting'
        TabBtn = $null; TabCloseBtn = $null; TabBorder = $null
        Content = $null; LogBox = $null; StatusLbl = $null; StopBtn = $null
    }
    [void]$script:sessions.Add($s)
    return $s
}

function Get-Session([int]$Id) {
    return $script:sessions | Where-Object { $_.Id -eq $Id } | Select-Object -First 1
}

function Set-ActiveSession([int]$Id) {
    foreach ($s in $script:sessions) {
        if (-not $s.Content) { continue }
        if ($s.Id -eq $Id) {
            $s.Content.Visibility = 'Visible'
            $s.TabBorder.Background = $brBg
            $s.TabBorder.BorderBrush = $brBlueBtn
            $s.TabBtn.Foreground = $brText
        } else {
            $s.Content.Visibility = 'Collapsed'
            $s.TabBorder.Background = [Windows.Media.Brushes]::Transparent
            $s.TabBorder.BorderBrush = [Windows.Media.Brushes]::Transparent
            $s.TabBtn.Foreground = $brMuted
        }
    }
    $script:activeSessionId = $Id
}

function New-SessionContent($session) {
    $grid = New-Object Windows.Controls.Grid
    $grid.Background = $script:brBg
    $grid.HorizontalAlignment = 'Stretch'
    $grid.VerticalAlignment = 'Stretch'

    $row1 = New-Object Windows.Controls.RowDefinition
    $row1.Height = 'Auto'
    $row2 = New-Object Windows.Controls.RowDefinition
    $row2.Height = '*'
    [void]$grid.RowDefinitions.Add($row1)
    [void]$grid.RowDefinitions.Add($row2)

    # Header: DockPanel — кнопка STOP всегда справа
    $hdr = New-Object Windows.Controls.DockPanel
    $hdr.Margin = New-Object Windows.Thickness(14,10,14,8)
    $hdr.Background = [Windows.Media.Brushes]::Transparent
    $hdr.LastChildFill = $true

    $stopBtn = New-Object Windows.Controls.Button
    $stopBtn.Content = 'ОСТАНОВИТЬ'
    $stopBtn.FontSize = 11
    $stopBtn.FontWeight = [Windows.FontWeights]::SemiBold
    $stopBtn.Padding = New-Object Windows.Thickness(14,5,14,5)
    $stopBtn.Foreground = $script:brRed
    $stopBtn.Background = [Windows.Media.Brushes]::Transparent
    $stopBtn.BorderBrush = $script:brRed
    $stopBtn.BorderThickness = New-Object Windows.Thickness(1)
    $stopBtn.Cursor = 'Hand'
    $stopBtn.MinWidth = 130
    $stopBtn.Height = 30
    $sid = $session.Id
    $stopBtn.Add_Click({ param($x,$e) Stop-Session $sid }.GetNewClosure())
    [Windows.Controls.DockPanel]::SetDock($stopBtn, 'Right')
    [void]$hdr.Children.Add($stopBtn)

    $infoPanel = New-Object Windows.Controls.StackPanel
    $infoPanel.Orientation = 'Horizontal'
    $infoPanel.VerticalAlignment = 'Center'
    $infoPanel.Margin = New-Object Windows.Thickness(0,0,14,0)

    $nameTb = New-Text $session.Name 14 $script:brTermCyan 'SemiBold'
    $nameTb.Margin = New-Object Windows.Thickness(0,0,0,0)
    [void]$infoPanel.Children.Add($nameTb)

    $stateTb = New-Text '● CONNECTING...' 11 $script:brAmber 'SemiBold'
    $stateTb.Margin = New-Object Windows.Thickness(18,2,0,0)
    [void]$infoPanel.Children.Add($stateTb)

    [Windows.Controls.DockPanel]::SetDock($infoPanel, 'Left')
    [void]$hdr.Children.Add($infoPanel)

    Windows.Controls.Grid::SetRow($hdr, 0)
    [void]$grid.Children.Add($hdr)

    # Separator
    $sep = New-Object Windows.Controls.Border
    $sep.Height = 1
    $sep.Background = $script:brBorder
    $sep.HorizontalAlignment = 'Stretch'
    $sep.VerticalAlignment = 'Top'
    $sep.Margin = New-Object Windows.Thickness(14,44,14,0)
    [Windows.Controls.Grid]::SetRow($sep, 0)
    [void]$grid.Children.Add($sep)

    # Log
    $logBox = New-Object Windows.Controls.TextBox
    $logBox.IsReadOnly = $true
    $logBox.FontFamily = New-Object Windows.Media.FontFamily('Consolas')
    $logBox.FontSize = 12
    $logBox.Foreground = $script:brTermFg
    $logBox.Background = [Windows.Media.Brushes]::Transparent
    $logBox.BorderThickness = New-Object Windows.Thickness(0)
    $logBox.VerticalScrollBarVisibility = 'Auto'
    $logBox.HorizontalScrollBarVisibility = 'Auto'
    $logBox.TextWrapping = 'NoWrap'
    $logBox.AcceptsReturn = $true
    $logBox.Margin = New-Object Windows.Thickness(14,0,14,10)
    Windows.Controls.Grid::SetRow($logBox, 1)
    [void]$grid.Children.Add($logBox)

    $session.Content = $grid
    $session.LogBox = $logBox
    $session.StatusLbl = $stateTb
    $session.StopBtn = $stopBtn

    [void]$SessionHost.Children.Add($grid)
}

function New-SessionTab($session) {
    $border = New-Object Windows.Controls.Border
    $border.CornerRadius = New-Object Windows.CornerRadius(6)
    $border.BorderThickness = New-Object Windows.Thickness(1)
    $border.BorderBrush = [Windows.Media.Brushes]::Transparent
    $border.Background = [Windows.Media.Brushes]::Transparent
    $border.Margin = New-Object Windows.Thickness(2,0,2,0)

    $grid = New-Object Windows.Controls.Grid
    $col1 = New-Object Windows.Controls.ColumnDefinition
    $col1.Width = 'Auto'
    $col2 = New-Object Windows.Controls.ColumnDefinition
    $col2.Width = '*'
    $col3 = New-Object Windows.Controls.ColumnDefinition
    $col3.Width = 'Auto'
    [void]$grid.ColumnDefinitions.Add($col1)
    [void]$grid.ColumnDefinitions.Add($col2)
    [void]$grid.ColumnDefinitions.Add($col3)

    $dot = New-Text '●' 12 $brAmber
    $dot.Margin = New-Object Windows.Thickness(12,0,4,0)
    Windows.Controls.Grid::SetColumn($dot, 0)
    [void]$grid.Children.Add($dot)

    $tb = New-Text $session.Name 12 $brMuted
    $tb.Margin = New-Object Windows.Thickness(0,6,10,6)
    Windows.Controls.Grid::SetColumn($tb, 1)
    [void]$grid.Children.Add($tb)

    $closeBtn = New-Object Windows.Controls.Button
    $closeBtn.Content = '×'
    $closeBtn.FontSize = 14
    $closeBtn.FontWeight = [Windows.FontWeights]::Bold
    $closeBtn.Foreground = $brMuted
    $closeBtn.Background = [Windows.Media.Brushes]::Transparent
    $closeBtn.BorderThickness = New-Object Windows.Thickness(0)
    $closeBtn.Padding = New-Object Windows.Thickness(8,2,8,2)
    $closeBtn.Cursor = 'Hand'
    $closeBtn.Add_MouseEnter({ $closeBtn.Foreground = $brRed })
    $closeBtn.Add_MouseLeave({ if ($script:activeSessionId -ne $session.Id) { $closeBtn.Foreground = $brMuted } })
    $sid = $session.Id
    $closeBtn.Add_Click({ param($x,$e) Close-Session $sid }.GetNewClosure())
    Windows.Controls.Grid::SetColumn($closeBtn, 2)
    [void]$grid.Children.Add($closeBtn)

    $border.Child = $grid

    # Клик по панели — выбрать сессию (кроме клика по крестику)
    $tb.MouseLeftButtonDown.Add({ param($x,$e) Set-ActiveSession $sid }) | Out-Null
    $dot.MouseLeftButtonDown.Add({ param($x,$e) Set-ActiveSession $sid }) | Out-Null

    $session.TabBtn = $tb
    $session.TabCloseBtn = $closeBtn
    $session.TabBorder = $border

    [void]$TabPanel.Children.Add($border)
}

function Append-Log($session, [string]$msg) {
    try {
        $line = ("{0:HH:mm:ss}  {1}`r`n" -f (Get-Date), $msg)
        $session.LogBox.AppendText($line)
        $session.LogBox.ScrollToEnd()
    } catch {}
}

function Set-SessionStatus($session, [string]$state) {
    $session.Status = $state
    $info = switch ($state) {
        'up'      { @('●', 'ONLINE',         $script:brTermGrn) }
        'error'   { @('●', 'ERROR',          $script:brRed) }
        'stopped' { @('●', 'OFFLINE',        $script:brDim) }
        default   { @('●', 'CONNECTING...',  $script:brAmber) }
    }
    try {
        $session.StatusLbl.Text = "$($info[0]) $($info[1])"
        $session.StatusLbl.Foreground = $info[2]
    } catch {}
}

function Stop-Session([int]$Id) {
    $s = Get-Session $Id
    if (-not $s) { return }
    try {
        if ($s.Proc -and -not $s.Proc.HasExited) {
            Append-Log $s '[VPN] STOPPING...'
            & taskkill.exe /F /T /PID $s.Proc.Id 2>$null | Out-Null
        }
    } catch {}
    foreach ($f in @($s.LogFile, $s.RunnerPs)) {
        if ($f -and (Test-Path -LiteralPath $f)) {
            try { Remove-Item -LiteralPath $f -Force -ErrorAction SilentlyContinue } catch {}
        }
    }
    Set-SessionStatus $s 'stopped'
    Append-Log $s '[--] SESSION TERMINATED'
    try { if ($s.StopBtn) { $s.StopBtn.IsEnabled = $false; $s.StopBtn.Content = 'ОСТАНОВЛЕН' } } catch {}
    Update-Counters
}

function Close-Session([int]$Id) {
    $s = Get-Session $Id
    if (-not $s) { return }
    $isActive = $s.Proc -and -not $s.Proc.HasExited
    if ($isActive) {
        $r = [System.Windows.MessageBox]::Show(
            "Сессия `"$($s.Name)`" активна. Остановить и закрыть вкладку?",
            'Закрытие сессии', 'YesNo', 'Question')
        if ($r -ne 'Yes') { return }
    }
    Stop-Session $Id
    try { [void]$SessionHost.Children.Remove($s.Content) } catch {}
    try { [void]$TabPanel.Children.Remove($s.TabBorder) } catch {}
    [void]$script:sessions.Remove($s)
    if ($script:activeSessionId -eq $Id) {
        if ($script:sessions.Count -gt 0) {
            Set-ActiveSession $script:sessions[0].Id
        } else {
            $script:activeSessionId = 0
        }
    }
    Update-Counters
}

function Start-Session([string]$BatPath) {
    foreach ($s in $script:sessions) {
        if ($s.BatPath -eq $BatPath -and $s.Proc -and -not $s.Proc.HasExited) {
            Set-ActiveSession $s.Id; return
        }
    }
    $session = New-Session $BatPath
    New-SessionTab $session
    New-SessionContent $session
    Set-ActiveSession $session.Id
    Append-Log $session "[VPN] LAUNCH :: $BatPath"

    $dir  = Split-Path -Parent $BatPath
    $file = Split-Path -Leaf $BatPath
    $stamp = [DateTime]::Now.ToString('yyyyMMdd-HHmmss-fff')
    $logFile = Join-Path $env:TEMP ("vpn-launcher-$stamp.log")
    $runner  = Join-Path $env:TEMP ("vpn-launcher-$stamp.ps1")

    $dirEsc  = $dir  -replace "'", "''"
    $fileEsc = $file -replace "'", "''"
    $logEsc  = $logFile -replace "'", "''"

    $body = @"
`$ErrorActionPreference = 'Continue'
`$dir  = '$dirEsc'
`$file = '$fileEsc'
`$log  = '$logEsc'
cmd.exe /c "pushd ```"`$dir```" && call ```"`$file```"" *>&1 |
    Out-File -LiteralPath `$log -Encoding UTF8
"@
    [IO.File]::WriteAllText($runner, $body, (New-Object Text.UTF8Encoding($true)))

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = (Join-Path $PSHOME 'powershell.exe')
    $psi.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$runner`""
    $psi.WorkingDirectory = $env:TEMP
    $psi.UseShellExecute = $true; $psi.WindowStyle = 'Hidden'

    $p = [System.Diagnostics.Process]::Start($psi)
    $session.Proc = $p
    $session.LogFile = $logFile
    $session.RunnerPs = $runner
    $session.LogPos = 0
    $session.Ready = $false; $session.SoftUp = $false
    $session.StartTime = Get-Date
    Set-SessionStatus $session 'starting'
    Append-Log $session "[VPN] LOG :: $logFile"
    Start-PollTimer
    Update-Counters
}

# ============================================================
#                    POLL TIMER
# ============================================================
$pollTimer = New-Object Windows.Threading.DispatcherTimer
$pollTimer.Interval = [TimeSpan]::FromMilliseconds(400)

function Start-PollTimer {
    if (-not $pollTimer.IsEnabled) { $pollTimer.Start() }
}

function Read-NewLogLines([string]$file, [int]$fromPos) {
    $r = @{ Text = ''; NewPos = $fromPos }
    try {
        $fs = [IO.File]::Open($file, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
        try {
            $sr = New-Object IO.StreamReader($fs, [Text.Encoding]::UTF8, $true)
            $all = $sr.ReadToEnd()
        } finally { $fs.Close() }
        if ($all.Length -gt $fromPos) { $r.Text = $all.Substring($fromPos); $r.NewPos = $all.Length }
    } catch {}
    return $r
}

$pollTimer.Add_Tick({
    try {
        $anyStarting = $false
        foreach ($s in @($script:sessions)) {
            if (-not $s.Proc) { continue }
            if ($s.LogFile -and (Test-Path -LiteralPath $s.LogFile)) {
                $r = Read-NewLogLines $s.LogFile $s.LogPos
                if ($r.Text.Length -gt 0) {
                    $s.LogPos = $r.NewPos
                    foreach ($line in ($r.Text -split "`r?`n")) {
                        if ($line.Trim().Length -gt 0) { Append-Log $s $line.TrimEnd() }
                    }
                    if ($r.Text -match 'Initialization Sequence Completed') { $s.Ready = $true }
                }
            }
            if ($s.Proc.HasExited) {
                if ($s.Ready -and $s.Status -ne 'stopped') {
                    Set-SessionStatus $s 'stopped'; Append-Log $s '[--] VPN DISCONNECTED'
                } elseif ($s.Status -ne 'stopped') {
                    Set-SessionStatus $s 'error'; Append-Log $s "[!!] EXIT CODE $($s.Proc.ExitCode)"
                }
                $s.Proc = $null; continue
            }
            if ($s.Ready -and $s.Status -eq 'starting') {
                Set-SessionStatus $s 'up'; Append-Log $s '[++] VPN ONLINE'; Update-Counters
            } elseif ($s.Status -eq 'starting') {
                $anyStarting = $true
                $elapsed = if ($s.StartTime) { ((Get-Date) - $s.StartTime).TotalSeconds } else { 0 }
                if (-not $s.SoftUp -and $elapsed -ge [double]$cfg.vpn_soft_up_after) {
                    $s.SoftUp = $true
                    Set-SessionStatus $s 'up'
                    Append-Log $s "[++] VPN ONLINE (по таймауту, маркер не найден)"
                    Update-Counters
                }
                if ($elapsed -gt $cfg.vpn_timeout) {
                    Set-SessionStatus $s 'error'; Append-Log $s "[!!] TIMEOUT $($cfg.vpn_timeout)s"
                }
            }
        }
        if (-not $anyStarting) { $pollTimer.Stop() }
    } catch {}
})

# ============================================================
#                    ОТКРЫТИЕ ФАЙЛА
# ============================================================
function Open-File([string]$path) {
    try {
        if ([IO.Path]::GetExtension($path).ToLower() -eq '.bat') {
            $dir  = Split-Path -Parent $path
            $file = Split-Path -Leaf $path
            Start-Process -FilePath 'cmd.exe' `
                -ArgumentList "/c pushd `"$dir`" && call `"$file`"" ` `
                -WorkingDirectory $env:TEMP
        } else {
            Start-Process -FilePath $path
        }
    } catch {
        [System.Windows.MessageBox]::Show("$_", 'ERROR') | Out-Null
    }
}

# ============================================================
#                        EVENTS
# ============================================================
$BtnRefresh.Add_Click({
    $StatusLeft.Text = 'Сканирую VPN...'
    Scan-Vpn; Render-VpnList
    $StatusLeft.Text = 'Сканирую файлы...'
    Scan-Vnc; Build-Tree
    Update-Counters
})

$BtnDisconnectAll.Add_Click({
    $active = @($script:sessions | Where-Object { $_.Proc -and -not $_.Proc.HasExited })
    if ($active.Count -eq 0) { return }
    $r = [System.Windows.MessageBox]::Show(
        "Остановить все активные VPN ($($active.Count))?",
        'Подтверждение', 'YesNo', 'Question')
    if ($r -eq 'Yes') { foreach ($s in $active) { Stop-Session $s.Id } }
    Update-Counters
})

$TxtVpnSearch.Add_TextChanged({ Render-VpnList })
$TxtSearch.Add_TextChanged({ Build-Tree })

$LstVpn.Add_MouseDoubleClick({
    $item = $LstVpn.SelectedItem
    if ($item -and $item.Tag) { Start-Session $item.Tag }
})
$LstVpn.Add_KeyDown({
    param($s, $e)
    if ($e.Key -eq 'Enter' -and $LstVpn.SelectedItem -and $LstVpn.SelectedItem.Tag) {
        Start-Session $LstVpn.SelectedItem.Tag
    }
})

$TreeVnc.Add_MouseDoubleClick({
    $item = $TreeVnc.SelectedItem
    if ($item -and $item.Tag) {
        $tag = $item.Tag.ToString()
        if (Test-Path -LiteralPath $tag -PathType Leaf) { Open-File $tag }
    }
})

$BtnOpenFile.Add_Click({
    $item = $TreeVnc.SelectedItem
    if (-not $item -or -not $item.Tag) { return }
    $tag = $item.Tag.ToString()
    if (Test-Path -LiteralPath $tag -PathType Leaf) { Open-File $tag }
})

$BtnShowInFolder.Add_Click({
    $item = $TreeVnc.SelectedItem
    if ($item -and $item.Tag) {
        $tag = $item.Tag.ToString()
        if (Test-Path -LiteralPath $tag -PathType Leaf) {
            Start-Process explorer.exe "/select,`"$tag`""
        } else {
            Start-Process explorer.exe $tag
        }
    } else {
        Start-Process explorer.exe $cfg.vnc_root
    }
})

$win.Add_Closing({
    try {
        $active = @($script:sessions | Where-Object { $_.Proc -and -not $_.Proc.HasExited })
        if ($active.Count -gt 0) {
            $r = [System.Windows.MessageBox]::Show(
                "Активных VPN: $($active.Count). Остановить перед выходом?",
                'Выход', 'YesNo', 'Question')
            if ($r -eq 'Yes') { foreach ($s in $active) { Stop-Session $s.Id } }
        }
    } catch {}
})

# Часы
$clockTimer = New-Object Windows.Threading.DispatcherTimer
$clockTimer.Interval = [TimeSpan]::FromSeconds(1)
$clockTimer.Add_Tick({ $StatusRight.Text = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') })
$clockTimer.Start()

# ============================================================
#                          START
# ============================================================
$win.Add_ContentRendered({
    $StatusLeft.Text = 'Сканирую VPN...'
    Scan-Vpn; Render-VpnList
    $StatusLeft.Text = 'Сканирую файлы...'
    Scan-Vnc; Build-Tree
    Update-Counters
})

# Тёмная тема заголовка и рамки окна (Windows 10 1903+ / Windows 11)
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class DwmDarkHelper {
    [DllImport("dwmapi.dll")]
    public static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int val, int size);
}
"@

$win.Add_SourceInitialized({
    try {
        $helper = New-Object System.Windows.Interop.WindowInteropHelper($win)
        $hwnd = $helper.Handle
        $dark = 1
        # attr 20: Windows 10 build 18985+ и Windows 11
        [void][DwmDarkHelper]::DwmSetWindowAttribute($hwnd, 20, [ref]$dark, 4)
        # attr 19: Windows 10 build 17763-18984
        [void][DwmDarkHelper]::DwmSetWindowAttribute($hwnd, 19, [ref]$dark, 4)
        # attr 34: цвет рамки (Windows 11). BGR #0d1117 → 0x17110d
        $borderColor = 0x17110d
        [void][DwmDarkHelper]::DwmSetWindowAttribute($hwnd, 34, [ref]$borderColor, 4)
    } catch {}
})

[void]$win.ShowDialog()