def emision_recibos(request, idGrupo):

	global boletas_editadas
	global recibo_enviado_bool
	global credito_usado


	try:
		fecha_ultimo_recibo = Instituto.objects.get(id=request.user.instituto.id).fecha_ultimo_recibo
		fecha_ultimo_recibo_format = str(fecha_ultimo_recibo.day) + "/" + str(fecha_ultimo_recibo.month) + "/" + str(fecha_ultimo_recibo.year)
		if dt.datetime.strptime(fecha_ultimo_recibo_format, "%d/%m/%Y").date() <= dt.date.today():
			fecha_ultimo_recibo_format = None
	except:
		fecha_ultimo_recibo_format = None
	

	grupo=Grupo.objects.get(id=idGrupo, instituto=request.user.instituto)
	alumnos_grupo=grupo.alumnos.all()


	boletas=Factura.objects.filter(grupo=grupo, instituto=request.user.instituto, esta_paga=False).order_by('-mes_facturacion', '-id')
	
	comprobantes=grupo.facturas.filter(esta_paga=False).order_by('mes_facturacion', 'id')

	responsables=grupo.responsables.all().order_by('nombre')
	credito = 0
	credito_viejo = 0
	if responsables:
		for responsable in responsables:
			try:
				credito+=responsable.credito.importe
				credito_viejo+=responsable.credito.importe
			except ObjectDoesNotExist:
				credito+=0
				credito_viejo+=0
			try:
				credito+=Credito.objects.filter(instituto=request.user.instituto, resp_admin=responsable).aggregate(Sum('importe'))['importe__sum']
			except:
				credito+=0
				

	try:
		ultimo_pago=Recibo.objects.filter(grupo=idGrupo, instituto=request.user.instituto).order_by('-id')[0].fecha_pago
	except:
		ultimo_pago="No hay pagos registrados"
				

	if request.method == "POST":
		if Instituto.objects.get(id=request.user.instituto.id).fecha_ultimo_recibo:
			fecha_ultimo_recibo = Instituto.objects.get(id=request.user.instituto.id).fecha_ultimo_recibo
			fecha_ultimo_recibo_format = str(fecha_ultimo_recibo.day) + "/" + str(fecha_ultimo_recibo.month) + "/" + str(fecha_ultimo_recibo.year)
			#evaluar si request.POST["fecha_recibo"] es anterior a la fecha actual menos 10 dias

			if dt.datetime.strptime(request.POST["fecha_recibo"], "%d/%m/%Y").date() < dt.date.today() - dt.timedelta(days=10):
				messages.error(request, 'La fecha del recibo no puede superar los diez días de retraso.')
				return redirect('mensaje_emision_recibo_error')

			if dt.datetime.strptime(request.POST["fecha_recibo"], "%d/%m/%Y").date() < dt.datetime.strptime(fecha_ultimo_recibo_format, "%d/%m/%Y").date():
				messages.error(request, 'La fecha del recibo no puede ser anterior a la fecha del último recibo emitido.')
				return redirect('mensaje_emision_recibo_error')

			if dt.datetime.strptime(request.POST["fecha_recibo"], "%d/%m/%Y").date() > dt.date.today() + dt.timedelta(days=10):
				messages.error(request, 'La fecha del recibo no puede superar los diez días de antelación.')
				return redirect('mensaje_emision_recibo_error')

		if request.POST.get('importe'):


			importe_a_formatear = request.POST.get('importe')
			if "." in importe_a_formatear:
				last_dot_index = importe_a_formatear.rindex(".")
				decimal_part = importe_a_formatear[last_dot_index+1:]
				if len(decimal_part) <= 2:
					importe_formateado = importe_a_formatear[:last_dot_index] + "," + decimal_part
					importe_formateado = float(importe_formateado.replace('.', '').replace(',', '.'))
				else:
					importe_formateado = float(importe_a_formatear.replace('.', '').replace(',', '.'))
			else:
				importe_formateado = float(importe_a_formatear.replace('.', '').replace(',', '.'))
			importe_formateado=Decimal(importe_formateado) #Si no lo paso a decimal, No funcionan las cuentas, ya que todo lo demas esta en decimal
			importe_formateado=round(importe_formateado, 2)
			id_list=request.POST.getlist('boxeses')
			forma_pago=request.POST.get('forma_pago')
			observaciones=request.POST.get('observaciones')
			if (credito_viejo == 0 and id_list._len() != 0 and importe_formateado > 0) or (credito_viejo > 0 and id_list.__len_() != 0):
				importe = importe_formateado  #debo smarle al importe lo que puedan tener en la tabla credito
				importe_recibo=importe
				boletas_abonadas=[]
				fecha_recibo=request.POST["fecha_recibo"]
				fecha_recibo=fecha_recibo.split("/")
				fecha_recibo=fecha_recibo[2]+"-"+fecha_recibo[1]+"-"+fecha_recibo[0]  #formato fecha para mysql
				#no estoy contemplando en todo esto el pronto pago y el interes
				#tampoco estan contemplados responsables multiples, tanto en el guardado de los recibos, como en la tabla credito
				#faltan muchos datos de los recibos y las facturas, como el cae. Mirar tabla recibos del programa de escritorio
				boletas=Factura.objects.filter(id__in=id_list, instituto=request.user.instituto).order_by('mes_facturacion', 'id')
				boletas=sorted(boletas, key=lambda x: x.alumnos.nombre)
				boletas=sorted(boletas, reverse=True, key=lambda x: x.mes_facturacion)
				sin_responsable=True  #Modificar o eliminar cuando contemple multiples responsables
				importe_boletas_abonadas=0
				boletas_list = []
				pagao = 0
				for factura in boletas:
					if sin_responsable==True:        #Modificar o eliminar cuando contemple multiples responsables (Esto es para que no recalcule el importe en cada iteracion)
						if factura.alumnos.responsable_admin != None:   #Tengo que poner un else, y en ese caso saltar esa iteracion de bucle (tal vez almacenar el estudiante para avisar al colegio)
							#credito=Credito.objects.get_or_create(responsable_admin=factura.alumnos.responsable_admin, instituto=request.user.instituto)  #creo el credito si no existe. Esto devuelve una tupla con el objeto y un booleano (True si lo tuvo q crear)
							try:
								credito=Credito.objects.filter(responsable_admin=factura.alumnos.responsable_admin, instituto=request.user.instituto).aggregate(Sum('importe'))['importe__sum']
								credito_consulta=Credito.objects.filter(responsable_admin=factura.alumnos.responsable_admin, instituto=request.user.instituto)[0]
							except:
								credito=0
							if credito == None:
								credito=0
							importe = importe + credito
							sin_responsable=False
						else:
							messages.error(request, 'El grupo no tiene responsable administrativo')
							return redirect('mensaje_emision_recibo_error')
					if importe > 0:   #Este limite es por si seleccionan tres boletas y solo se pone el monto de dos de ellas, para que no se efectue ningun cambio sobre la que se abono
						if factura.calcula_pronto_pago() != 0: #Si la boleta de la iteracion actual tiene pronto pago
							if boletas_editadas:  #Si hay boletas editadas
								coincidencia = False
								for boleta_editada in boletas_editadas:
									if factura.id == boleta_editada[0]:
										nuevo_importe_editado = boleta_editada[2]
										coincidencia = True
										break
								if coincidencia == True:
									importe_boletas_abonadas+=nuevo_importe_editado-factura.pagado
									boletas_abonadas.append(factura)
									if importe + factura.pagado < nuevo_importe_editado:
										pagao=importe + factura.pagado
										boletas_list.append([factura, pagao, False, importe])  #pagao hace referencia a todo lo que la boleta tiene abonado despues de este pago
										importe=0                                              #importe hace referencia a lo que se pagó en esta ocasión
										break
									elif importe + factura.pagado == nuevo_importe_editado:
										pagao=importe + factura.pagado
										boletas_list.append([factura, pagao, True, importe])
										importe=0
										break
									elif importe + factura.pagado > nuevo_importe_editado:
										importe=importe-(nuevo_importe_editado-factura.pagado)
										pagao=nuevo_importe_editado                   #En este caso, como la boleta tiene abonado todo el importe, se pone el resultado del calculo del pronto pago
										abonado_esta_vez=nuevo_importe_editado-factura.pagado
										boletas_list.append([factura, pagao, True, abonado_esta_vez])
								if not coincidencia:  #Si hay boletas editadas, pero no esta la que estoy iterando
									importe_boletas_abonadas+=factura.calcula_pronto_pago()-factura.pagado
									boletas_abonadas.append(factura)
									if importe + factura.pagado < factura.calcula_pronto_pago():
										pagao=importe + factura.pagado
										boletas_list.append([factura, pagao, False, importe])  #pagao hace referencia a todo lo que la boleta tiene abonado despues de este pago
										importe=0                                              #importe hace referencia a lo que se pagó en esta ocasión
										break
									elif importe + factura.pagado == factura.calcula_pronto_pago():
										pagao=importe + factura.pagado
										boletas_list.append([factura, pagao, True, importe])
										importe=0
										break
									elif importe + factura.pagado > factura.calcula_pronto_pago():
										importe=importe-(factura.calcula_pronto_pago()-factura.pagado)
										pagao=factura.calcula_pronto_pago()                   #En este caso, como la boleta tiene abonado todo el importe, se pone el resultado del calculo del pronto pago
										abonado_esta_vez=factura.calcula_pronto_pago()-factura.pagado
										boletas_list.append([factura, pagao, True, abonado_esta_vez])
							else:  #Si no hay boletas editadas
								importe_boletas_abonadas+=factura.calcula_pronto_pago()-factura.pagado
								boletas_abonadas.append(factura)
								if importe + factura.pagado < factura.calcula_pronto_pago():
									pagao=importe + factura.pagado
									boletas_list.append([factura, pagao, False, importe])  #pagao hace referencia a todo lo que la boleta tiene abonado despues de este pago
									importe=0                                              #importe hace referencia a lo que se pagó en esta ocasión
									break
								elif importe + factura.pagado == factura.calcula_pronto_pago():
									pagao=importe + factura.pagado
									boletas_list.append([factura, pagao, True, importe])
									importe=0
									break
								elif importe + factura.pagado > factura.calcula_pronto_pago():
									importe=importe-(factura.calcula_pronto_pago()-factura.pagado)
									pagao=factura.calcula_pronto_pago()                   #En este caso, como la boleta tiene abonado todo el importe, se pone el resultado del calculo del pronto pago
									abonado_esta_vez=factura.calcula_pronto_pago()-factura.pagado
									boletas_list.append([factura, pagao, True, abonado_esta_vez])
						else: #Si la boleta de la iteracion actual no tiene pronto pago
							importe_boletas_abonadas+=factura.importe-factura.pagado
							boletas_abonadas.append(factura)
							if importe + factura.pagado < factura.importe:
								pagao=importe + factura.pagado
								boletas_list.append([factura, pagao, False, importe])  #pagao hace referencia a todo lo que la boleta tiene abonado despues de este pago
								importe=0                                              #importe hace referencia a lo que se pagó en esta ocasión
								break
							elif importe + factura.pagado == factura.importe:
								pagao=importe + factura.pagado
								boletas_list.append([factura, pagao, True, importe])
								importe=0
								break
							elif importe + factura.pagado > factura.importe:
								importe=importe-(factura.importe-factura.pagado)
								pagao=factura.importe                   #En este caso, como la boleta tiene abonado todo el importe, se pone el resultado del calculo del pronto pago
								abonado_esta_vez=factura.importe-factura.pagado
								boletas_list.append([factura, pagao, True, abonado_esta_vez])
				for boleta in boletas_list:
					if boleta[2] == False:
						if boleta[0].vencimientos.all():
							if boleta[1] > boleta[0].calcula_pronto_pago():
								boleta_error=Factura.objects.get(id=boleta[0].id, instituto=request.user.instituto)
								messages.error(request, f'La boleta {boleta_error.concepto} arroja un importe negativo')
								return redirect('mensaje_emision_recibo_error')
						else:
							if boleta[1] > boleta[0].importe:
								boleta_error=Factura.objects.get(id=boleta[0].id, instituto=request.user.instituto)
								messages.error(request, f'La boleta {boleta_error.concepto} arroja un importe negativo')
								return redirect('mensaje_emision_recibo_error')
				if sin_responsable == False:      #Si no hay responsables, no emite los recibos. Debe haber una forma mas elegante de hacer esto, como redirigir a la pagina de error sin llegar a este punto del codigo
					if credito > 0:
						usando_efectivo=importe_boletas_abonadas-importe_recibo #En los condicionales q siguen, se calcula cuanto se uso de saldo a favor, y cuanto queda
						if usando_efectivo > 0:
							usando_saldo_a_favor=usando_efectivo-credito
							if usando_saldo_a_favor < 0:
								usado_a_favor=credito-abs(usando_saldo_a_favor)
								queda_a_favor=abs(usando_saldo_a_favor) #abs devuelve el valor absoluto, es decir, si es menor, lo devuelve mayor
								#importe_recibo=importe_recibo+usado_a_favor  #Esto lo comente para que no se facture el saldo a favor que se está usando, ya que el mismo se factura cuando se genera
							elif usando_saldo_a_favor == 0:
								usado_a_favor=credito
								queda_a_favor=0
								#importe_recibo=importe_recibo+usado_a_favor #Esto lo comente para que no se facture el saldo a favor que se está usando, ya que el mismo se factura cuando se genera
							elif usando_saldo_a_favor > 0:
								usado_a_favor=credito
								queda_a_favor=0
								#importe_recibo=importe_recibo+usado_a_favor #Esto lo comente para que no se facture el saldo a favor que se está usando, ya que el mismo se factura cuando se genera
						elif usando_efectivo == 0:
							usado_a_favor=0
							queda_a_favor=credito
						else:
							usado_a_favor=0
							queda_a_favor=credito+abs(usando_efectivo)
					else:
						usado_a_favor=0
						usando_efectivo=importe_boletas_abonadas-importe_recibo
						if usando_efectivo > 0:
							queda_a_favor=credito
						elif usando_efectivo == 0:
							queda_a_favor=credito
						else:
							queda_a_favor=credito+abs(usando_efectivo)

					#Aca se almacena en el recibo el estado que tenian las boletas al momento de generar el recibo. Ademas, cual era la deuda total de esas boletas en ese momento
					estado_boletas = []
					adeudado_boletas_selecionadas = 0
					abonado_en_cada_boleta = []
					for factura in boletas_list:
						abonado_en_cada_boleta.append([factura[0].id, factura[3]]) #Esto no tiene nada que ver con el resto del bucle. Aca se almacena el id de la boleta y el abono que se le hizo, para saber desde el recibo cuanto se abono de cada boleta que esta cancelando
						if factura[0].grupo.excepcion_pronto_pago:
							adeudado_boletas_selecionadas += factura[0].importe - factura[0].pagado
							estado_boletas.append([factura[0].id, factura[0].importe, factura[0].pagado, factura[0].importe - factura[0].pagado])
						else:
							if factura[0].calcula_pronto_pago() != 0:
								if boletas_editadas:  #Si hay boletas editadas
									coincidencia = False
									for boleta_editada in boletas_editadas:
										if factura[0].id == boleta_editada[0]:
											nuevo_importe_editado = boleta_editada[2]
											coincidencia = True
											break
									if coincidencia:  #Si hay boletas editadas, y esta la que estoy iterando
										#if factura[2] == True:
										adeudado_boletas_selecionadas += nuevo_importe_editado - factura[0].pagado
										estado_boletas.append([factura[0].id, nuevo_importe_editado, factura[0].pagado, nuevo_importe_editado - factura[0].pagado])
										#else:  #Si la boleta no esta pagada en su totalidad, no puedo calcular la deuda restandole lo pagado al importe editado, porque, al no estar totalmente abonada la boleta, cuando se termine la operacion, volvera a calcularse el pronto pago en funcion de la fecha actual
										#	adeudado_boletas_selecionadas += factura[0].calcula_pronto_pago() - factura[0].pagado
										#	estado_boletas.append([factura[0].id, nuevo_importe_editado, factura[0].pagado, factura[0].calcula_pronto_pago() - factura[0].pagado])
									if not coincidencia:  #Si hay boletas editadas, pero no esta la que estoy iterando
										adeudado_boletas_selecionadas += factura[0].calcula_pronto_pago() - factura[0].pagado
										estado_boletas.append([factura[0].id, factura[0].calcula_pronto_pago(), factura[0].pagado, factura[0].calcula_pronto_pago() - factura[0].pagado])
								else:
									adeudado_boletas_selecionadas += factura[0].calcula_pronto_pago() - factura[0].pagado
									estado_boletas.append([factura[0].id, factura[0].calcula_pronto_pago(), factura[0].pagado, factura[0].calcula_pronto_pago() - factura[0].pagado])
							else:
								adeudado_boletas_selecionadas += factura[0].importe - factura[0].pagado
								estado_boletas.append([factura[0].id, factura[0].importe, factura[0].pagado, factura[0].importe - factura[0].pagado])

					estado_boletas = json.dumps(estado_boletas, indent=4, sort_keys=True, default=str)
					abonado_en_cada_boleta = json.dumps(abonado_en_cada_boleta, indent=4, sort_keys=True, default=str)

					#inicio conexion con afip
					#if importe_recibo <= adeudado_boletas_selecionadas:   #Esto es para que no se incluya en la facturacion lo que se paga de mas
					#	importe_recibo = importe_recibo
					#else:
					#	importe_recibo = adeudado_boletas_selecionadas
					if credito > 0:   #En caso de que se usa credito del diseño viejo
						importe_recibo = importe_recibo + usado_a_favor
					if importe_recibo > 0:
						instituto=Instituto.objects.get(id=request.user.instituto.id)
						tipo_recibo = instituto.tipo_recibo
						punto_venta = PuntoVenta.objects.get(instituto=request.user.instituto).pv
						cuit_instituto = instituto.cuit
						cuit_responsable = boletas[0].alumnos.responsable_admin.cuit
						dni_responsable = boletas[0].alumnos.responsable_admin.num_doc
						if cuit_responsable and dni_responsable:
							dni_cuit_responsable = dni_responsable
							tipo_doc = 96
						else:
							if cuit_responsable:
								dni_cuit_responsable = cuit_responsable
								tipo_doc = 80
							else:
								dni_cuit_responsable = dni_responsable
								tipo_doc = 96
						datos_recibo=facturar(request, tipo_recibo=tipo_recibo, punto_venta=punto_venta, fecha_recibo=fecha_recibo, tipo_doc=tipo_doc, dni_cuit_responsable=dni_cuit_responsable, cuit_instituto=cuit_instituto, importe_recibo=importe_recibo)
						if datos_recibo['errores'] != []:
							messages.error(request, f"{datos_recibo['errores']}")	
							return redirect('mensaje_emision_recibo_error')
					#fin conexion con afip

					#Elimino el credito viejo, si es que se usó
					if credito > 0:
						if credito == usado_a_favor:
							credito_consulta.delete()
						elif credito > usado_a_favor:
							credito_consulta.importe = credito_consulta.importe - usado_a_favor
							credito_consulta.save()

					#Aca se crea el nuevo credito, si es que se puso plata de mas
					if credito > 0:  #Si se uso saldo a favor del diseño viejo
						queda_a_favor_nuevo = (usado_a_favor + queda_a_favor) - credito #queda_a_favor_nuevo = queda_a_favor - credito
					else:
						queda_a_favor_nuevo = queda_a_favor
					if queda_a_favor_nuevo > 0:
						grupo_para_credito=Grupo.objects.get(id=idGrupo, instituto=request.user.instituto)
						responsable_para_credito=ResponsableAdmin.objects.filter(grupo=grupo_para_credito, instituto=request.user.instituto)[0]
						credito=Credito.objects.create(resp_admin=responsable_para_credito, instituto=request.user.instituto, importe=queda_a_favor_nuevo, nro_recibo=datos_recibo['nro_recibo'])
									

					datos_vencimientos_pronto = []
					for boleta in boletas_list:
						if boleta[2] == True:   #si la boleta se cancelo totalmente
							boleta[0].pagado=boleta[1]
							boleta[0].esta_paga=True
							boleta[0].save()
							if boletas_editadas:
								coincidencia = False
								for boleta_editada in boletas_editadas:
									if boleta[0].id == boleta_editada[0]:
										nueva_fecha_vencimiento_editada = boleta_editada[1]
										nuevo_importe_editado = boleta_editada[2]
										nuevo_importe_pronto_pago_editado = boleta_editada[3]
										coincidencia = True
										break
								if coincidencia:
									boleta[0].importe=nuevo_importe_editado
									boleta[0].save()
									datos_vencimientos_pronto.append([boleta[0].id, nueva_fecha_vencimiento_editada, nuevo_importe_pronto_pago_editado])
								if not coincidencia:  #si hay boletas editadas, pero la boleta de la iteracion no esta en la lista de boletas editadas, significa que no se modifico
									if boleta[0].vencimientos.all():
										boleta[0].importe=boleta[0].calcula_pronto_pago()
										datos_vencimientos_pronto.append(revisa_vencimientos_pronto(boleta[0]))
										boleta[0].save()
									else:
										boleta[0].pagado=boleta[0].importe
										boleta[0].save()
							else:
								if boleta[0].vencimientos.all():
									boleta[0].importe=boleta[0].calcula_pronto_pago()
									datos_vencimientos_pronto.append(revisa_vencimientos_pronto(boleta[0]))
									boleta[0].save()
								else:
									boleta[0].pagado=boleta[0].importe
									boleta[0].save()
						else:
							if boletas_editadas:
								coincidencia = False
								for boleta_editada in boletas_editadas:
									if boleta[0].id == boleta_editada[0]:
										nueva_fecha_vencimiento_editada = boleta_editada[1]
										nuevo_importe_editado = boleta_editada[2]
										nuevo_importe_pronto_pago_editado = boleta_editada[3]
										coincidencia = True
										break
								if coincidencia:
									boleta[0].pagado=boleta[1]
									boleta[0].save()
									datos_vencimientos_pronto.append([boleta[0].id, nueva_fecha_vencimiento_editada, nuevo_importe_pronto_pago_editado])
								if not coincidencia:  #si hay boletas editadas, pero la boleta de la iteracion no esta en la lista de boletas editadas, significa que no se modifico
									if boleta[0].vencimientos.all():
										boleta[0].pagado=boleta[1]
										datos_vencimientos_pronto.append(revisa_vencimientos_pronto(boleta[0]))
										boleta[0].save()
									else:
										boleta[0].pagado=boleta[1]
										boleta[0].save()
							else:
								if boleta[0].vencimientos.all():
									boleta[0].pagado=boleta[1]
									datos_vencimientos_pronto.append(revisa_vencimientos_pronto(boleta[0]))
									boleta[0].save()
								else:
									boleta[0].pagado=boleta[1]
									boleta[0].save()

					datos_vencimientos_pronto = json.dumps(datos_vencimientos_pronto, indent=4, sort_keys=True, default=str) #se convierte a json para poder almacenarla en la base de datos

					#datos_vencimientos_pronto_lista = json.loads(datos_vencimientos_pronto) #convierte el json a lista

					if importe_recibo > 0:
						vencimiento_recibo=datos_recibo['vencimiento']
						vencimiento_recibo=vencimiento_recibo[0:4]+"-"+vencimiento_recibo[4:6]+"-"+vencimiento_recibo[6:]

						if tipo_doc == 96:
							tipo_doc = "DNI"
						elif tipo_doc == 80:
							tipo_doc = "CUIT"

						recibo=Recibo.objects.create(nro_recibo=datos_recibo['nro_recibo'], 
													fecha_vencimiento=vencimiento_recibo, 
													cae=datos_recibo['cae'], 
													pv=punto_venta, 
													fecha_pago=fecha_recibo, 
													importe=importe_recibo, 
													grupo=grupo, 
													responsable=boletas[0].alumnos.responsable_admin, 
													saldo_a_favor_usado=usado_a_favor, 
													saldo_a_favor_restante=queda_a_favor, 
													forma_pago=forma_pago, 
													observaciones=observaciones, 
													instituto=request.user.instituto, 
													pronto_pago=datos_vencimientos_pronto, 
													deuda_boletas_seleccionadas=adeudado_boletas_selecionadas, 
													estado_boletas=estado_boletas,
													datos_abono_facturas=abonado_en_cada_boleta,
													tipo_documento=tipo_doc,
													num_documento=dni_cuit_responsable,
													)
						recibo.save()

						for boleta in boletas_abonadas:
							recibo.factura.add(boleta)
							recibo.alumnos.add(boleta.alumnos)

					request.session['vengo_desde_emision'] = True

					if importe_recibo > 0:
						if forma_pago == "Crédito":
							tarjeta_credito=request.POST.get('tarjeta_credito')
							numero_tarjeta_credito=request.POST.get('numero_tarjeta_credito')
							lote_tarjeta_credito=request.POST.get('lote_tarjeta_credito')
							if numero_tarjeta_credito is not None and numero_tarjeta_credito != "" and lote_tarjeta_credito is not None and lote_tarjeta_credito != "":
								tarjeta=Tarjeta.objects.create(tarjeta=tarjeta_credito, numero=numero_tarjeta_credito, importe=importe_formateado, lote=lote_tarjeta_credito, recibo=recibo, l_debito=False, instituto=request.user.instituto)
							else:
								if numero_tarjeta_credito is not None and numero_tarjeta_credito != "":
									tarjeta=Tarjeta.objects.create(tarjeta=tarjeta_credito, numero=numero_tarjeta_credito, importe=importe_formateado, recibo=recibo, l_debito=False, instituto=request.user.instituto)
								elif lote_tarjeta_credito is not None and lote_tarjeta_credito != "":
									tarjeta=Tarjeta.objects.create(tarjeta=tarjeta_credito, importe=importe_formateado, lote=lote_tarjeta_credito, recibo=recibo, l_debito=False, instituto=request.user.instituto)
						elif forma_pago == "Transferencia":
							entidad_transferencia=request.POST.get('entidad_transferencia')
							fecha_transferencia=request.POST.get('fecha_transferencia')
							if fecha_transferencia is not None and fecha_transferencia != "":
								fecha_transferencia=fecha_transferencia[0:2]+"/"+fecha_transferencia[3:5]+"/"+fecha_transferencia[6:10]
								fecha_transferencia=datetime.strptime(fecha_transferencia, '%d/%m/%Y').date()
								transferencia=Cheque.objects.create(banco=entidad_transferencia, f_acredita=fecha_transferencia, importe=importe_formateado, recibo=recibo, ltrans=True, instituto=request.user.instituto)
							else:
								transferencia=Cheque.objects.create(banco=entidad_transferencia, importe=importe_formateado, recibo=recibo, ltrans=True, instituto=request.user.instituto)
						elif forma_pago == "Cheque":
							entidad_cheque=request.POST.get('entidad_cheque')
							nro_cheque=request.POST.get('nro_cheque')
							fecha_acreditacion=request.POST.get('acreditacion')
							if fecha_acreditacion is not None and fecha_acreditacion != "":
								fecha_acreditacion=fecha_acreditacion[6:10]+"-"+fecha_acreditacion[3:5]+"-"+fecha_acreditacion[0:2]
							if fecha_acreditacion is not None and fecha_acreditacion != "" and nro_cheque is not None and nro_cheque != "":
								cheque=Cheque.objects.create(banco=entidad_cheque, numero=nro_cheque, f_acredita=fecha_acreditacion, importe=importe_formateado, recibo=recibo, ltrans=False, instituto=request.user.instituto)
							else:
								if fecha_acreditacion is not None and fecha_acreditacion != "":
									cheque=Cheque.objects.create(banco=entidad_cheque, f_acredita=fecha_acreditacion, importe=importe_formateado, recibo=recibo, ltrans=False, instituto=request.user.instituto)
								elif nro_cheque is not None and nro_cheque != "":
									cheque=Cheque.objects.create(banco=entidad_cheque, numero=nro_cheque, importe=importe_formateado, recibo=recibo, ltrans=False, instituto=request.user.instituto)
						elif forma_pago == "Débito":
							tarjeta_debito=request.POST.get('tarjeta_debito')
							numero_tarjeta_debito=request.POST.get('numero_tarjeta_debito')
							lote_tarjeta_debito=request.POST.get('lote_tarjeta_debito')
							if numero_tarjeta_debito is not None and numero_tarjeta_debito != "" and lote_tarjeta_debito is not None and lote_tarjeta_debito != "":
								tarjeta=Tarjeta.objects.create(tarjeta=tarjeta_debito, numero=numero_tarjeta_debito, importe=importe_formateado, lote=lote_tarjeta_debito, recibo=recibo, l_debito=True, instituto=request.user.instituto)
							else:
								if numero_tarjeta_debito is not None and numero_tarjeta_debito != "":
									tarjeta=Tarjeta.objects.create(tarjeta=tarjeta_debito, numero=numero_tarjeta_debito, importe=importe_formateado, recibo=recibo, l_debito=True, instituto=request.user.instituto)
								elif lote_tarjeta_debito is not None and lote_tarjeta_debito != "":
									tarjeta=Tarjeta.objects.create(tarjeta=tarjeta_debito, importe=importe_formateado, lote=lote_tarjeta_debito, recibo=recibo, l_debito=True, instituto=request.user.instituto)
						elif forma_pago == "Mercado Pago":
							nro_operacion_mercado_pago=request.POST.get('nro_operacion_mercado_pago')
							if nro_operacion_mercado_pago is not None and nro_operacion_mercado_pago != "":
								mercado_pago=MercadoPago.objects.create(numero_operacion=nro_operacion_mercado_pago, importe=importe_formateado, recibo=recibo, instituto=request.user.instituto)
							else:
								mercado_pago=MercadoPago.objects.create(importe=importe_formateado, recibo=recibo, instituto=request.user.instituto)
						elif forma_pago == "Rapipago":
							nro_operacion_rapipago=request.POST.get('nro_operacion_rapipago')
							if nro_operacion_rapipago is not None and nro_operacion_rapipago != "":
								rapipago=Rapipago.objects.create(numero_operacion=nro_operacion_rapipago, importe=importe_formateado, recibo=recibo, instituto=request.user.instituto)
							else:
								rapipago=Rapipago.objects.create(importe=importe_formateado, recibo=recibo, instituto=request.user.instituto)
						elif forma_pago == "Pago mis Cuentas":
							nro_operacion_pago_mis_cuentas=request.POST.get('nro_operacion_pago_mis_cuentas')
							if nro_operacion_pago_mis_cuentas is not None and nro_operacion_pago_mis_cuentas != "":
								pago_mis_cuentas=PagoMisCuentas.objects.create(numero_operacion=nro_operacion_pago_mis_cuentas, importe=importe_formateado, recibo=recibo, instituto=request.user.instituto)
							else:
								pago_mis_cuentas=PagoMisCuentas.objects.create(importe=importe_formateado, recibo=recibo, instituto=request.user.instituto)

					boletas_editadas = []
					if importe_recibo > 0:
						instituto = Instituto.objects.get(id=request.user.instituto.id)
						instituto.fecha_ultimo_recibo = fecha_recibo
						instituto.save()

					if Instituto.objects.get(id=request.user.instituto.id).envio_automatico_recibos == True:
						if importe_recibo > 0:
							envia_recibo_desde_envio(request, recibo.id)
					if recibo_enviado_bool:
						if importe_recibo > 0:
							messages.success(request, '¡Recibo emitido y enviado!')
						else:
							messages.success(request, '¡Recibo emitido!')
					else:
						messages.success(request, '¡Recibo emitido!')
					recibo_enviado_bool = False
					if importe_recibo > 0:
						return redirect('mensaje_emision_recibo', recibo.grupo.id, recibo.id)
			else:
				if id_list._len_() == 0:
					messages.error(request, 'No se han seleccionado boletas')
				elif importe_formateado == 0:
					messages.error(request, 'No se ha definido un importe')
				elif importe_formateado < 0:
					messages.error(request, 'El importe no puede ser negativo')
				return redirect('mensaje_emision_recibo_error')
		else:
			id_list=request.POST.getlist('boxeses')
			if id_list._len_() == 0:
				messages.error(request, 'No se han seleccionado boletas')
			elif importe_formateado == 0:
				messages.error(request, 'No se ha definido un importe')
			elif importe_formateado < 0:
				messages.error(request, 'El importe no puede ser negativo')
			return redirect('mensaje_emision_recibo_error')
	else:
		#Reúno Memos destacados para mostrarlos en pantalla
		try:
			memos_destacados=Memos.objects.filter(grupo=grupo, importante=True, instituto=request.user.instituto).order_by('-id')
		except:
			memos_destacados=None


	grupos=Grupo.objects.filter(instituto=request.user.instituto).order_by('grupo')

	filtro_grupo = GrupoFilter(request.GET, queryset=grupos)

	boletas_editadas = []


	return render(request, 'mi_zeppelin/emision_recibos.html', {'grupo':grupo, 'comprobantes':comprobantes, 'filtro_grupo':filtro_grupo, 'grupo_busqueda':filtro_grupo.qs, 'ultimo_pago':ultimo_pago, 'credito':credito, 'credito_viejo': credito_viejo, "fecha_ultimo_recibo": fecha_ultimo_recibo_format, "memos_destacados": memos_destacados})