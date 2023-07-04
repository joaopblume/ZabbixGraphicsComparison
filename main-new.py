import mysql.connector
import config_mysql
import config_oracle
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib import pyplot as plt
import matplotlib.ticker as mticker
from datetime import datetime
import sys
import cx_Oracle


previous_month = datetime.strptime(sys.argv[1], '%m/%d/%y'), datetime.strptime(sys.argv[2], '%m/%d/%y')
current_month = datetime.strptime(sys.argv[3], '%m/%d/%y'), datetime.strptime(sys.argv[4], '%m/%d/%y')
host = sys.argv[5]
trigger_id = sys.argv[6]

p_month_num = previous_month[0].strftime('%m')
c_month_num = current_month[0].strftime('%m')
year = current_month[0].strftime('%y')


# def connect_oracledb():
#     oracle_connection = cx_Oracle.connect(f'{config_oracle.USERNAME}/{config_oracle.PASSWD}@//{config_oracle.HOST}:{config_oracle.PORT}/{config_oracle.SERVICE_NAME}')
#     return oracle_connection

def set_minor_ticks(x_vector):
    tick_list = []
    day = 1
    for i in x_vector:
        if i.day == day:
            tick_list.append(x_vector.index(i))
            day += 1
    difference = 31 - len(tick_list)
    gap = tick_list[-1] - tick_list[-2]
    last = tick_list[-1]
    next = last + gap
    while difference != 0:
        tick_list.append(next)
        difference -= 1
        next += gap
    return tick_list


def set_major_ticks(x_vector):
    tick_list = []
    day = 1
    for i in x_vector:
        if i.day == day:
            tick_list.append(x_vector.index(i))
            day += 3
    difference = 31 - len(tick_list)
    gap = tick_list[-1] - tick_list[-2]
    last = tick_list[-1]
    next = last + gap
    while difference != 0:
        tick_list.append(next)
        difference -= 1
        next += gap
    return tick_list


# connection to zabbix mysql
def connect_mysqldb():
    mysql_connection = mysql.connector.connect(host=config_mysql.HOST,
                                               port=config_mysql.PORT,
                                               user=config_mysql.USERNAME,
                                               passwd=config_mysql.PASSWD,
                                               database=config_mysql.DATABASE)
    return mysql_connection


def search_item(mysql_connection):
    mysql_cursor = mysql_connection.cursor()
    mysql_cursor.execute(f"select i.itemid, h.hostid, i.name"
                         f" from items i, functions f, triggers t, hosts h"
                         f" where  h.host = '{host}'"
                         f" and t.triggerid = '{trigger_id}'"
                         f" and h.hostid = i.hostid"
                         f" and t.triggerid = f.triggerid"
                         f"  and i.itemid = f.itemid")

    list = mysql_cursor.fetchall()[0]
    itemid = list[0]
    hostid = list[1]
    iname = list[2]
    return itemid, hostid, iname


def get_values(mysql_connection, itemid, hostid):
    mysql_cursor = mysql_connection.cursor()
    mysql_cursor.execute(f"select FROM_UNIXTIME(clock), value_avg"
                         f" from trends t, items i, hosts h"
                         f" where i.hostid=h.hostid"
                         f" and t.itemid = '{itemid}'"
                         f" and t.itemid = i.itemid "
                         f" and h.hostid='{hostid}'"
                         f" and clock BETWEEN UNIX_TIMESTAMP('{current_month[0]}') and UNIX_TIMESTAMP('{current_month[1]}') order by clock")
    current = mysql_cursor.fetchall()
    if len(current) < 1:
        mysql_cursor.execute(f"select FROM_UNIXTIME(clock), value"
                             f" from history_uint t, items i, hosts h"
                             f" where i.hostid=h.hostid"
                             f" and t.itemid = '{itemid}'"
                             f" and t.itemid = i.itemid"
                             f" and h.hostid='{hostid}'"
                             f" and clock BETWEEN UNIX_TIMESTAMP('{current_month[0]}') and UNIX_TIMESTAMP('{current_month[1]}') order by clock")
        current = mysql_cursor.fetchall()

    mysql_cursor.execute(f"select FROM_UNIXTIME(clock), value_avg"
                         f" from trends t, items i, hosts h"
                         f" where i.hostid=h.hostid"
                         f" and t.itemid = '{itemid}'"
                         f" and t.itemid = i.itemid "
                         f" and h.hostid='{hostid}'"
                         f" and clock BETWEEN UNIX_TIMESTAMP('{previous_month[0]}') and UNIX_TIMESTAMP('{previous_month[1]}') order by clock")

    previous = mysql_cursor.fetchall()
    if len(previous) < 1:
        mysql_cursor.execute(f"select FROM_UNIXTIME(clock), value"
                             f" from history_uint t, items i, hosts h"
                             f" where i.hostid=h.hostid"
                             f" and t.itemid = '{itemid}'"
                             f" and t.itemid = i.itemid"
                             f" and h.hostid='{hostid}'"
                             f" and clock BETWEEN UNIX_TIMESTAMP('{previous_month[0]}') and UNIX_TIMESTAMP('{previous_month[1]}') order by clock")
        previous = mysql_cursor.fetchall()

    current_y = []
    current_x = []
    previous_y = []
    previous_x = []

    for registro in range(0, len(current) - 1):
        current_y.append(current[registro][1])
        current_x.append(current[registro][0])

    for registro in range(0, len(previous) - 1):
        previous_y.append(previous[registro][1])
        previous_x.append(previous[registro][0])

    return [(current_x, current_y), (previous_x, previous_y)]


class Graph:
    def __init__(self):
        self.image = Figure()

    def mount_graph(self):
        previous_month_name = previous_month[0].strftime('%B')
        current_month_name = current_month[0].strftime('%B')
        title = f"[{item_name}] - {previous_month_name} - {current_month_name}"
        tick_num = [x for x in range(1, 32)]
        axes = self.image.gca()
        self.image.set_size_inches(9.5, 4)

        ticks_loc = set_ticks(current_x)
        axes.set_title(title)
        axes.set_xticks(ticks_loc, minor=True)
        axes.set_xticks(ticks_loc, minor=False)
        axes.xaxis.set_major_locator(mticker.FixedLocator(ticks_loc))
        axes.set_xticklabels(tick_num)
        axes.plot([x for x in range(1, len(current_x) + 1)], current_y, color='#003B9A', label=f"{current_month_name}")
        axes.plot([x for x in range(1, len(previous_x) + 1)], previous_y, color='#0082AE', label=f"{previous_month_name}")
        for i in ([axes.xaxis.label, axes.yaxis.label] + axes.get_xticklabels() + axes.get_yticklabels()):
            i.set_fontsize(8)

        axes.legend()
        axes.grid(True)
        # print(type(self.image))
        # plot = self.image.plot()
        # fig = plot.get_figure()
        axes.figure.savefig('/home/joao/grafico_teste.png')
        # self.image.plot().get_figure().savefig('/home/joao/grafico_teste.png')
        # self.image.figure.show()


mysql = connect_mysqldb()
# oracle = connect_oracledb()

item_id, host_id, item_name = search_item(mysql)
current, previous = get_values(mysql, item_id, host_id)
current_x, current_y = current
previous_x, previous_y = previous

graph = Graph()
graph.mount_graph()
# controls datetime set
# def calendar(date_box):
#     data_calendar.show()
#     if date_box == 1:
#         data_calendar.bt_ok.clicked.connect(lambda: set_date(1))
#     elif date_box == 2:
#         data_calendar.bt_ok.clicked.connect(lambda: set_date(2))
#     elif date_box == 3:
#         data_calendar.bt_ok.clicked.connect(lambda: set_date(3))
#     elif date_box == 4:
#         data_calendar.bt_ok.clicked.connect(lambda: set_date(4))


# set defined date to date_box
# def set_date(date_box):
#     current_data = data_calendar.calendario.selectedDate()
#     data_calendar.bt_ok.clicked.disconnect()
#     data_calendar.close()
#     if date_box == 1:
#         index.data1.setDate(current_data)
#     elif date_box == 2:
#         index.data2.setDate(current_data)
#     elif date_box == 3:
#         index.data1_2.setDate(current_data)
#     elif date_box == 4:
#         index.data2_2.setDate(current_data)


# create a list of hosts in selected host groups
# def search_hosts(h, connection):
#     mysql_cursor = connection.cursor()
#     mysql_cursor.execute(f"SELECT host FROM hosts WHERE host like '%{h}%' and status = 0")
#     host_group = mysql_cursor.fetchall()
#     # index.cb_hosts_2.clear()
#     hosts = []
#     for host in host_group:
#         hosts.append(host[0])
#     for item in hosts:
#         index.cb_hosts_2.addItem(item)


# look for name of available items
# def search_items_name(host_name, connection):
#     # if len(h) > 0:
#     #     global l_names
#     #     global hostid
#     l_names = []
#     mysql_cursor = connection.cursor()
#     mysql_cursor.execute(f"SELECT hostid  FROM hosts WHERE host = '{host_name}'")
#     hostid = mysql_cursor.fetchone()[0]
#     mysql_cursor.execute(f"select i.name from items i, hosts h where h.hostid = '{hostid}' and i.hostid=h.hostid and i.status <> 1")
#     all_names = mysql_cursor.fetchall()
#     for i_name in all_names:
#         l_names.append(i_name[0])


# class Graph:
#     def __init__(self, xy):
#         self.widget = None
#         self.canvas = None
#         self.axes = None
#         self.dateFormat = mdates.DateFormatter('%d/%m %Hh')
#         self.graph = Figure()
#         self.x, self.y, *self.aditional = xy
#         if len(xy) > 2:
#             self.double = True
#         else:
#             self.double = False
#
#     def set_parameter(self, name):
#         if self.double:
#             self.graph.set_size_inches(9.5, 4)
#             first_list = self.aditional[0][0].strftime("%d/%m/%Y %H:%M:%S")
#         else:
#             self.graph.set_size_inches(9.5, 2)
#             first_list = self.x[0].strftime("%d/%m/%Y %H:%M:%S")
#         self.axes = self.graph.gca()
#         last_list = self.x[len(self.x) - 1].strftime("%d/%m/%Y %H:%M:%S")
#         axes_title = f"[{name}] {first_list} - {last_list}"
#         self.axes.set_title(axes_title)
#
#     def mount_graph(self, color='black', label=''):
#         if self.double:
#             self.axes.plot([x for x in range(1, len(self.aditional[0]) + 1)], self.aditional[1], color='green', label=f"Period 1")
#             self.axes.plot([x for x in range(1, len(self.x) + 1)], self.y, color='orange', label=f"Period 2")
#
#         else:
#             self.axes.plot(self.x, self.y, color=color, label=label)
#         self.axes.xaxis.set_major_formatter(self.dateFormat)
#         for i in ([self.axes.xaxis.label, self.axes.yaxis.label] + self.axes.get_xticklabels() + self.axes.get_yticklabels()):
#             i.set_fontsize(8)
#         self.axes.legend()
#         self.axes.grid(True)
#         self.canvas = FigureCanvas(self.graph)
#
#     def plot_graph(self, scene, posx, posy):
#         self.widget = scene.addWidget(self.canvas)
#         self.widget.setPos(posx, posy)
#
#
# def alter_vision(v, graph_list):
#     graph1, graph2, graph3 = graph_list
#     graph1.setPos(0, 8)
#     graph3.setPos(1000, 1000)
#     if v == 1:
#         graph2.setPos(0, 225)
#     else:
#         graph2.setPos(1000, 1000)
#
#
# def calculate(connection):
#     scene = QtWidgets.QGraphicsScene()
#     plotted_graphs.graphicsView_3.setScene(scene)
#     scene.setSceneRect(0, 0, 900, 450)
#
#     hora1 = index.data1.dateTime().toString("yyyy-MM-dd hh:mm:ss")
#     hora2 = index.data1_2.dateTime().toString("yyyy-MM-dd hh:mm:ss")
#     hora3 = index.data2.dateTime().toString("yyyy-MM-dd hh:mm:ss")
#     hora4 = index.data2_2.dateTime().toString("yyyy-MM-dd hh:mm:ss")
#     name = index.cb_items.currentText()
#
#     mysql_cursor = connection.cursor(buffered=True)
#     mysql_cursor.execute(f"select itemid from items i, hosts h where i.name='{name}' and h.hostid='{hostid}' and i.hostid=h.hostid")
#     itemid = mysql_cursor.fetchone()[0]
#     mysql_cursor.execute(f"select FROM_UNIXTIME(clock), value_avg from trends t, items i, hosts h where i.hostid=h.hostid and t.itemid = '{itemid}' and t.itemid = i.itemid and h.hostid='{hostid}' and clock BETWEEN UNIX_TIMESTAMP('{hora1}') and UNIX_TIMESTAMP('{hora2}') order by clock")
#     first = mysql_cursor.fetchall()
#     print(f"select FROM_UNIXTIME(clock), value_avg from trends t, items i, hosts h where i.hostid=h.hostid and t.itemid = '{itemid}' and t.itemid = i.itemid and h.hostid='{hostid}' and clock BETWEEN UNIX_TIMESTAMP('{hora1}') and UNIX_TIMESTAMP('{hora2}') order by clock")
#     if len(first) < 1:
#         mysql_cursor.execute(f"select FROM_UNIXTIME(clock), value from history_uint t, items i, hosts h where i.hostid=h.hostid and t.itemid = '{itemid}' and t.itemid = i.itemid and h.hostid='{hostid}' and clock BETWEEN UNIX_TIMESTAMP('{hora1}') and UNIX_TIMESTAMP('{hora2}') order by clock")
#         first = mysql_cursor.fetchall()
#         print(f"select FROM_UNIXTIME(clock), value from history_uint t, items i, hosts h where i.hostid=h.hostid and t.itemid = '{itemid}' and t.itemid = i.itemid and h.hostid='{hostid}' and clock BETWEEN UNIX_TIMESTAMP('{hora1}') and UNIX_TIMESTAMP('{hora2}') order by clock")
#     mysql_cursor.execute(f"select FROM_UNIXTIME(clock), value_avg from trends t, items i, hosts h where i.hostid=h.hostid and t.itemid = '{itemid}' and t.itemid = i.itemid and h.hostid='{hostid}' and clock BETWEEN UNIX_TIMESTAMP('{hora3}') and UNIX_TIMESTAMP('{hora4}') order by clock")
#     second = mysql_cursor.fetchall()
#     if len(second) < 1:
#         mysql_cursor.execute(f"select FROM_UNIXTIME(clock), value from history_uint t, items i, hosts h where i.hostid=h.hostid and t.itemid = '{itemid}' and t.itemid = i.itemid and h.hostid='{hostid}' and clock BETWEEN UNIX_TIMESTAMP('{hora3}') and UNIX_TIMESTAMP('{hora4}') order by clock")
#         second = mysql_cursor.fetchall()
#     vertical1 = []
#     horizontal1 = []
#     vertical2 = []
#     horizontal2 = []
#     for registro in range(0, len(first) - 1):
#         vertical1.append(first[registro][1])
#         horizontal1.append(first[registro][0])
#
#     for registro in range(0, len(second) - 1):
#         vertical2.append(second[registro][1])
#         horizontal2.append(second[registro][0])
#
#     period1 = Graph((horizontal1, vertical1))
#     period2 = Graph((horizontal2, vertical2))
#     both_periods = Graph((horizontal1, vertical1, horizontal2, vertical2))
#
#     period1.set_parameter(name)
#     period2.set_parameter(name)
#     both_periods.set_parameter(name)
#
#     period1.mount_graph('blue', 'Period 1')
#     period2.mount_graph('red', 'Period 2')
#     both_periods.mount_graph()
#
#     period1.plot_graph(scene, 0, 8)
#     period2.plot_graph(scene, 0, 225)
#     both_periods.plot_graph(scene, 1000, 1000)
#     # axes1.plot(horizontal1, vertical1, color='blue', label="Period 1", )
#     # axes1.xaxis.set_major_formatter(dataFormat)
#     # for i in ([axes1.xaxis.label, axes1.yaxis.label] + axes1.get_xticklabels() + axes1.get_yticklabels()):
#     #     i.set_fontsize(8)
#
#     # axes2.plot(horizontal2, vertical2, color='red', label="Period 2")
#     # axes2.xaxis.set_major_formatter(dataFormat)
#     # for i in ([axes2.xaxis.label, axes2.yaxis.label] + axes2.get_xticklabels() + axes2.get_yticklabels()):
#     #     i.set_fontsize(8)
#
#     # b_axes.plot([x for x in range(1, len(horizontal1) + 1)], vertical1, color='green', label=f"Period 1")
#     # b_axes.plot([x for x in range(1, len(horizontal2) + 1)], vertical2, color='orange', label=f"Period 2")
#     # for i in ([b_axes.xaxis.label, b_axes.yaxis.label] + b_axes.get_xticklabels() + b_axes.get_yticklabels()):
#     #     i.set_fontsize(8)
#
#     # axes1.legend()
#     # axes1.grid(True)
#     # axes2.legend()
#     # axes2.grid(True)
#     # b_axes.legend()
#     # b_axes.grid(True)
#
#     # canvas_axes1 = FigureCanvas(period1)
#     # canvas_axes2 = FigureCanvas(period2)
#     # canvas_both_axes = FigureCanvas(both_periods)
#     # both_axes_widget = scene1.addWidget(canvas_both_axes)
#     # axes1_widget = scene1.addWidget(canvas_axes1)
#     # axes2_widget = scene1.addWidget(canvas_axes2)
#     # both_axes_widget.setPos(1000, 1000)
#     # axes1_widget.setPos(0, 8)
#     # axes2_widget.setPos(0, 225)
#
#     plotted_graphs.show()
#
#     plotted_graphs.pushButton.clicked.connect(lambda: alter_vision(1, [period1.widget, period2.widget, both_periods.widget]))
#     plotted_graphs.pushButton_2.clicked.connect(lambda: alter_vision(2, [both_periods.widget, period1.widget, period2.widget]))
#
#
# def show_separate_graphics(widgets):
#     widget1, widget2, widget3 = widgets
#     widget1.setPos(0, 8)
#     widget2.setPos(0, 225)
#     widget3.setPos(1000, 1000)
#
#
# def show__graph(widgets):
#     widget1, widget2, widget3 = widgets
#     widget1.setPos(1000, 1000)
#     widget2.setPos(1000, 1000)
#     widget3.setPos(0, 0)
#
#
# app = QtWidgets.QApplication([])
# conn = connect_db()
# # import interfaces
# index = uic.loadUi('index.ui')
# data_calendar = uic.loadUi('data.ui')
# plotted_graphs = uic.loadUi('plotted_graphs.ui')
#
#
# index.bt1.clicked.connect(lambda: calendar(1))
# index.bt2.clicked.connect(lambda: calendar(2))
# index.bt1_2.clicked.connect(lambda: calendar(3))
# index.bt2_2.clicked.connect(lambda: calendar(4))
#
# index.cb_hosts.currentTextChanged.connect(lambda: (search_hosts(index.cb_hosts.currentText(), conn)))
# index.cb_hosts_2.currentTextChanged.connect(lambda: (search_items_name(index.cb_hosts_2.currentText(), conn)))
#
# index.bt_confirm.clicked.connect(lambda: calculate(conn))
#
# hg = ['ABT Castro', 'Afubra', 'Agrale', 'Boxprint', 'Datacom', 'Diementz', 'Eletrorastro', 'Herval', 'Pegada', 'W2a']
# for host_group in hg:
#     index.cb_hosts.addItem(host_group)
#
# index.show()
#
# try:
#     app.exec()
# except:
#     print('error')

